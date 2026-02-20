import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobTarget(str, Enum):
    CLOUD = "cloud"
    PC = "pc"
    ANY = "any"


DB_PATH = Path(__file__).parent.parent.parent / "jobs.db"


@contextmanager
def get_db():
    conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Inicializa la base de datos con la tabla de jobs."""
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                target TEXT NOT NULL DEFAULT 'any',
                input_path TEXT NOT NULL,
                output_path TEXT,
                worker_id TEXT,
                error_message TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """
        )

        columns = [row[1] for row in conn.execute("PRAGMA table_info(jobs)").fetchall()]
        if "target" not in columns:
            conn.execute("ALTER TABLE jobs ADD COLUMN target TEXT NOT NULL DEFAULT 'any'")

        conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON jobs(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_target ON jobs(target)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON jobs(created_at)")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ip_limits (
                ip TEXT PRIMARY KEY,
                request_count INTEGER NOT NULL DEFAULT 0,
                blocked INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            )
        """
        )
        conn.commit()


def create_job(input_path: str, target: JobTarget = JobTarget.ANY) -> str:
    """Crea un nuevo job y retorna su ID."""
    job_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO jobs (id, status, target, input_path, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (job_id, JobStatus.PENDING, target, input_path, now, now),
        )
        conn.commit()

    return job_id


def get_job(job_id: str) -> Optional[dict]:
    """Obtiene información de un job por ID."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return dict(row) if row else None


def get_next_pending_job() -> Optional[dict]:
    """Obtiene el siguiente job pendiente (para el worker)."""
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT * FROM jobs 
            WHERE status = ? 
            ORDER BY created_at ASC 
            LIMIT 1
        """,
            (JobStatus.PENDING,),
        ).fetchone()
        return dict(row) if row else None


def dequeue_next_pending_job(worker_id: str) -> Optional[dict]:
    """Obtiene y reclama atómicamente el siguiente job pendiente para un worker."""
    now = datetime.utcnow().isoformat()

    if worker_id == "render-worker":
        allowed_targets = (JobTarget.CLOUD, JobTarget.ANY)
    elif worker_id.startswith("local-worker"):
        allowed_targets = (JobTarget.PC, JobTarget.ANY)
    else:
        allowed_targets = (JobTarget.ANY, JobTarget.CLOUD, JobTarget.PC)

    with get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")

        row = conn.execute(
            """
            SELECT id
            FROM jobs
            WHERE status = ? AND target IN (?, ?)
            ORDER BY created_at ASC
            LIMIT 1
            """,
            (JobStatus.PENDING, allowed_targets[0], allowed_targets[1]),
        ).fetchone()

        if not row:
            conn.rollback()
            return None

        job_id = row["id"]

        cursor = conn.execute(
            """
            UPDATE jobs
            SET status = ?, worker_id = ?, updated_at = ?
            WHERE id = ? AND status = ?
            """,
            (JobStatus.PROCESSING, worker_id, now, job_id, JobStatus.PENDING),
        )

        if cursor.rowcount == 0:
            conn.rollback()
            return None

        job_row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        conn.commit()

        return dict(job_row) if job_row else None


def update_job_status(
    job_id: str,
    status: JobStatus,
    output_path: Optional[str] = None,
    error_message: Optional[str] = None,
    worker_id: Optional[str] = None,
):
    """Actualiza el estado de un job."""
    now = datetime.utcnow().isoformat()

    with get_db() as conn:
        conn.execute(
            """
            UPDATE jobs 
            SET status = ?, output_path = ?, error_message = ?, worker_id = ?, updated_at = ?
            WHERE id = ?
        """,
            (status, output_path, error_message, worker_id, now, job_id),
        )
        conn.commit()


def claim_job(job_id: str, worker_id: str) -> bool:
    """Marca un job como en procesamiento por un worker específico."""
    now = datetime.utcnow().isoformat()

    with get_db() as conn:
        cursor = conn.execute(
            """
            UPDATE jobs 
            SET status = ?, worker_id = ?, updated_at = ?
            WHERE id = ? AND status = ?
        """,
            (JobStatus.PROCESSING, worker_id, now, job_id, JobStatus.PENDING),
        )
        conn.commit()
        return cursor.rowcount > 0


def delete_job(job_id: str) -> None:
    """Elimina un job de la base de datos."""
    with get_db() as conn:
        conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        conn.commit()


def register_ip_request(ip: str, max_requests: int) -> tuple[bool, int]:
    """Registra un request por IP. Retorna (permitido, total_requests)."""
    now = datetime.utcnow().isoformat()

    with get_db() as conn:
        row = conn.execute("SELECT request_count, blocked FROM ip_limits WHERE ip = ?", (ip,)).fetchone()

        if not row:
            conn.execute(
                "INSERT INTO ip_limits (ip, request_count, blocked, updated_at) VALUES (?, ?, ?, ?)",
                (ip, 1, 0, now),
            )
            conn.commit()
            return True, 1

        current_count = int(row["request_count"])
        is_blocked = int(row["blocked"]) == 1

        if is_blocked:
            return False, current_count

        new_count = current_count + 1
        should_block = 1 if new_count > max_requests else 0

        conn.execute(
            "UPDATE ip_limits SET request_count = ?, blocked = ?, updated_at = ? WHERE ip = ?",
            (new_count, should_block, now, ip),
        )
        conn.commit()

        return should_block == 0, new_count
