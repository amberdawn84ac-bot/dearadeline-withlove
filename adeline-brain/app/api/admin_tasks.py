"""
Admin Tasks API - /api/admin/tasks endpoints
Administrative tasks like seeding the bookshelf database.
"""
import logging
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel

from app.schemas.api_models import UserRole
from app.api.middleware import require_role, get_current_user_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin/tasks", tags=["admin-tasks"])

class TaskResponse(BaseModel):
    success: bool
    message: str
    task_id: str

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str  # "running", "completed", "failed"
    progress: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

# In-memory task tracking (in production, use Redis or database)
task_status = {}

@router.post(
    "/setup-bookshelf",
    response_model=TaskResponse,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def setup_bookshelf(
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
) -> TaskResponse:
    """
    One-click setup: Run migrations and seed the bookshelf database.
    
    This will:
    1. Run database migrations to create/update tables
    2. Run the seed script to populate the Book table
    3. Verify the setup completed successfully
    
    Returns:
    - Task ID that can be used to check progress
    """
    import uuid
    task_id = str(uuid.uuid4())
    
    # Initialize task status
    task_status[task_id] = {
        "status": "running",
        "progress": "Starting bookshelf setup...",
        "result": None,
        "error": None,
        "started_by": user_id,
        "started_at": str(Path(__file__).resolve().parents[2])
    }
    
    # Add background task to run setup
    background_tasks.add_task(run_bookshelf_setup, task_id, user_id)
    
    logger.info(f"[Admin] Bookshelf setup task {task_id} started by {user_id}")
    
    return TaskResponse(
        success=True,
        message="Bookshelf setup started. This will run migrations and seed the database.",
        task_id=task_id
    )

@router.post(
    "/seed-bookshelf",
    response_model=TaskResponse,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def seed_bookshelf(
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
) -> TaskResponse:
    """
    Trigger the bookshelf seeding script to populate the Book table.
    
    This will:
    - Fetch books from Standard Ebooks and Project Gutenberg APIs
    - Generate embeddings using OpenAI
    - Assign curriculum tracks and reading levels
    - Populate the Book table with searchable content
    
    Returns:
    - Task ID that can be used to check progress
    """
    import uuid
    task_id = str(uuid.uuid4())
    
    # Initialize task status
    task_status[task_id] = {
        "status": "running",
        "progress": "Starting seed script...",
        "result": None,
        "error": None,
        "started_by": user_id,
        "started_at": str(Path(__file__).resolve().parents[2] / "scripts" / "seed_bookshelf.py")
    }
    
    # Add background task to run the seed script
    background_tasks.add_task(run_seed_script, task_id, user_id)
    
    logger.info(f"[Admin] Bookshelf seeding task {task_id} started by {user_id}")
    
    return TaskResponse(
        success=True,
        message="Bookshelf seeding started. Use the task ID to check progress.",
        task_id=task_id
    )

@router.post(
    "/seed-scripture",
    response_model=TaskResponse,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def seed_scripture(
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
) -> TaskResponse:
    """
    Seed Hippocampus with 55 key scripture passages via Sefaria (Everett Fox preferred).
    Covers DISCIPLESHIP, TRUTH_HISTORY, JUSTICE_CHANGEMAKING, GOVERNMENT_ECONOMICS,
    HEALTH_NATUROPATHY, CREATION_SCIENCE, and HOMESTEADING tracks.
    Run once; Sefaria also lazy-caches on demand during lessons.
    """
    import uuid as _uuid
    task_id = str(_uuid.uuid4())
    task_status[task_id] = {
        "status": "running",
        "progress": "Starting scripture seed...",
        "result": None,
        "error": None,
        "started_by": user_id,
        "started_at": "",
    }

    async def _run():
        try:
            result = subprocess.run(
                [sys.executable, "-m", "scripts.seed_scripture"],
                cwd=Path(__file__).resolve().parents[2],
                capture_output=True,
                text=True,
                timeout=3600,
            )
            if result.returncode == 0:
                task_status[task_id]["status"] = "completed"
                task_status[task_id]["progress"] = "Scripture seeding completed"
                task_status[task_id]["result"] = {"stdout": result.stdout}
            else:
                task_status[task_id]["status"] = "failed"
                task_status[task_id]["error"] = result.stderr
        except Exception as e:
            task_status[task_id]["status"] = "failed"
            task_status[task_id]["error"] = str(e)

    background_tasks.add_task(_run)
    logger.info(f"[Admin] Scripture seeding task {task_id} started by {user_id}")
    return TaskResponse(
        success=True,
        message="Scripture seeding started. Use the task ID to check progress.",
        task_id=task_id,
    )


@router.post(
    "/seed-nature-lost-vault",
    response_model=TaskResponse,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def seed_nature_lost_vault(
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
) -> TaskResponse:
    """
    Seed Hippocampus with NatureLostVault.com content.
    
    Covers:
    - HEALTH_NATUROPATHY: Medicinal plants (lemon balm, boneset, chaga, perilla)
    - HOMESTEADING: Survival foods, edible weeds, eggshell fertilizer
    - CREATION_SCIENCE: Traditional building techniques (Roman concrete, rammed earth)
    
    Source: https://naturelostvault.com
    """
    import uuid as _uuid
    task_id = str(_uuid.uuid4())
    task_status[task_id] = {
        "status": "running",
        "progress": "Starting Nature Lost Vault seed...",
        "result": None,
        "error": None,
        "started_by": user_id,
        "started_at": "",
    }

    async def _run():
        try:
            result = subprocess.run(
                [sys.executable, "-m", "scripts.seed_nature_lost_vault"],
                cwd=Path(__file__).resolve().parents[2],
                capture_output=True,
                text=True,
                timeout=3600,
            )
            if result.returncode == 0:
                task_status[task_id]["status"] = "completed"
                task_status[task_id]["progress"] = "Nature Lost Vault seeding completed"
                task_status[task_id]["result"] = {"stdout": result.stdout}
            else:
                task_status[task_id]["status"] = "failed"
                task_status[task_id]["error"] = result.stderr
        except Exception as e:
            task_status[task_id]["status"] = "failed"
            task_status[task_id]["error"] = str(e)

    background_tasks.add_task(_run)
    logger.info(f"[Admin] Nature Lost Vault seeding task {task_id} started by {user_id}")
    return TaskResponse(
        success=True,
        message="Nature Lost Vault seeding started. Use the task ID to check progress.",
        task_id=task_id,
    )


@router.get(
    "/task/{task_id}",
    response_model=TaskStatusResponse,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def get_task_status(
    task_id: str,
    user_id: str = Depends(get_current_user_id),
) -> TaskStatusResponse:
    """
    Get the status of an admin task.
    
    Args:
    - task_id: UUID of the task to check
    
    Returns:
    - Current status, progress, and results of the task
    """
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = task_status[task_id]
    
    return TaskStatusResponse(
        task_id=task_id,
        status=task["status"],
        progress=task.get("progress"),
        result=task.get("result"),
        error=task.get("error")
    )

@router.get(
    "/tasks",
    response_model=Dict[str, TaskStatusResponse],
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def list_tasks(
    user_id: str = Depends(get_current_user_id),
) -> Dict[str, TaskStatusResponse]:
    """
    List all admin tasks and their status.
    
    Returns:
    - Dictionary of task_id -> TaskStatusResponse
    """
    return {
        task_id: TaskStatusResponse(
            task_id=task_id,
            status=task["status"],
            progress=task.get("progress"),
            result=task.get("result"),
            error=task.get("error")
        )
        for task_id, task in task_status.items()
    }

async def run_bookshelf_setup(task_id: str, user_id: str):
    """
    Run migrations and seed script in the background.
    """
    try:
        # Step 1: Run migrations
        task_status[task_id]["progress"] = "Running database migrations..."
        
        migration_path = Path(__file__).resolve().parents[2] / "prisma" / "migrations"
        migrate_result = subprocess.run(
            [sys.executable, "-m", "prisma", "db", "push"],
            cwd=Path(__file__).resolve().parents[2],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutes for migrations
        )
        
        if migrate_result.returncode != 0:
            task_status[task_id]["status"] = "failed"
            task_status[task_id]["error"] = f"Migration failed: {migrate_result.stderr}"
            logger.error(f"[Admin] Setup task {task_id} migration failed: {migrate_result.stderr}")
            return
        
        # Step 2: Run seed script
        task_status[task_id]["progress"] = "Running seed script..."
        await run_seed_script(task_id, user_id, is_setup=True)
        
    except subprocess.TimeoutExpired:
        task_status[task_id]["status"] = "failed"
        task_status[task_id]["error"] = "Setup timed out"
        logger.error(f"[Admin] Setup task {task_id} timed out")
        
    except Exception as e:
        task_status[task_id]["status"] = "failed"
        task_status[task_id]["error"] = str(e)
        logger.error(f"[Admin] Setup task {task_id} failed with exception: {e}")

async def run_seed_script(task_id: str, user_id: str, is_setup: bool = False, script_name: str = "seed_bookshelf"):
    """
    Run a seed script in the background and update task status.
    
    Args:
        task_id: The task ID for status tracking
        user_id: The user who initiated the task
        is_setup: Whether this is part of a setup task
        script_name: Name of the script to run (without .py extension)
    """
    try:
        # Get the path to the seed script
        script_path = Path(__file__).resolve().parents[2] / "scripts" / f"{script_name}.py"
        
        # Update progress
        task_status[task_id]["progress"] = f"Running seed script: {script_path}"
        
        # Run the seed script
        result = subprocess.run(
            [sys.executable, "-m", f"scripts.{script_name}"],
            cwd=Path(__file__).resolve().parents[2],
            capture_output=True,
            text=True,
            timeout=3600,  # 1 hour timeout
        )
        
        if result.returncode == 0:
            # Success
            task_status[task_id]["status"] = "completed"
            task_status[task_id]["progress"] = "Seed script completed successfully"
            task_status[task_id]["result"] = {
                "stdout": result.stdout,
                "return_code": result.returncode
            }
            logger.info(f"[Admin] Seed task {task_id} completed successfully")
        else:
            # Error
            task_status[task_id]["status"] = "failed"
            task_status[task_id]["error"] = result.stderr
            task_status[task_id]["result"] = {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
            logger.error(f"[Admin] Seed task {task_id} failed: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        task_status[task_id]["status"] = "failed"
        task_status[task_id]["error"] = "Seed script timed out after 1 hour"
        logger.error(f"[Admin] Seed task {task_id} timed out")
        
    except Exception as e:
        task_status[task_id]["status"] = "failed"
        task_status[task_id]["error"] = str(e)
        logger.error(f"[Admin] Seed task {task_id} failed with exception: {e}")


# ── Canonical management endpoints ───────────────────────────────────────────

@router.post(
    "/seed-canonicals",
    response_model=TaskResponse,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def seed_canonicals(
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
) -> TaskResponse:
    """
    Pre-generate 25 foundational canonical lessons (21 per-track + 4 cross-track
    bridging topics). Skips slugs that already exist in the canonical store.
    Run once after deployment; safe to re-run.
    """
    import uuid as _uuid
    task_id = str(_uuid.uuid4())
    task_status[task_id] = {
        "status": "running",
        "progress": "Starting canonical pre-seed...",
        "result": None,
        "error": None,
        "started_by": user_id,
        "started_at": "",
    }

    async def _run():
        try:
            result = subprocess.run(
                [sys.executable, "-m", "scripts.seed_canonicals"],
                cwd=Path(__file__).resolve().parents[2],
                capture_output=True,
                text=True,
                timeout=7200,  # 2 hour timeout — 25 full orchestrator runs
            )
            if result.returncode == 0:
                task_status[task_id]["status"] = "completed"
                task_status[task_id]["progress"] = "Canonical pre-seed completed"
                task_status[task_id]["result"] = {"stdout": result.stdout}
            else:
                task_status[task_id]["status"] = "failed"
                task_status[task_id]["error"] = result.stderr
        except Exception as e:
            task_status[task_id]["status"] = "failed"
            task_status[task_id]["error"] = str(e)

    background_tasks.add_task(_run)
    logger.info(f"[Admin] Canonical seeding task {task_id} started by {user_id}")
    return TaskResponse(
        success=True,
        message="Canonical pre-seed started. Use the task ID to check progress.",
        task_id=task_id,
    )


@router.get(
    "/canonicals/pending",
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def list_pending_canonicals(
    user_id: str = Depends(get_current_user_id),
) -> list:
    """
    List all canonical lessons awaiting admin approval.
    High-stakes tracks and researcher-activated lessons are held here.
    """
    from app.connections.canonical_store import canonical_store
    return await canonical_store.list_pending()


@router.post(
    "/canonicals/{slug}/approve",
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def approve_canonical(
    slug: str,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """
    Approve a pending canonical lesson, making it live for all students.
    Clears pendingApproval flag in DB and publishes to Redis cache.
    """
    from app.connections.canonical_store import canonical_store
    approved = await canonical_store.approve(slug)
    if not approved:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=404,
            detail=f"No pending canonical found for slug '{slug}'",
        )
    logger.info(f"[Admin] Canonical approved — {slug} by {user_id}")
    return {"approved": True, "slug": slug}
