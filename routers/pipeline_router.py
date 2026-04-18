"""Pipeline API — stage-by-stage script generation."""
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from database import get_db, SessionLocal
from models import Script, PipelineStage, SystemPrompt
from routers.character import get_host_info

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])
executor = ThreadPoolExecutor(max_workers=2)

STAGE_ORDER = ["intro", "part1", "part2", "part3"]


@router.get("/{script_id}/stages")
def get_stages(script_id: int, db: Session = Depends(get_db)):
    """Get all pipeline stages for a script."""
    script = db.query(Script).get(script_id)
    if not script:
        return JSONResponse({"error": "Script not found"}, status_code=404)

    stages = db.query(PipelineStage).filter(
        PipelineStage.script_id == script_id
    ).order_by(PipelineStage.id).all()

    # Group by stage_name
    grouped = {}
    for s in stages:
        if s.stage_name not in grouped:
            grouped[s.stage_name] = []
        grouped[s.stage_name].append({
            "id": s.id,
            "stage_name": s.stage_name,
            "result_text": s.result_text,
            "status": s.status,
            "attempt_number": s.attempt_number,
            "prompt_used": s.prompt_used,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        })

    # Build response with stage order
    result = []
    for stage_name in STAGE_ORDER:
        attempts = grouped.get(stage_name, [])
        accepted = next((a for a in attempts if a["status"] == "accepted"), None)
        result.append({
            "stage_name": stage_name,
            "attempts": attempts,
            "accepted": accepted,
            "status": "accepted" if accepted else ("generating" if any(a["status"] == "generating" for a in attempts) else ("pending" if not attempts else "draft")),
        })

    return {
        "script_id": script_id,
        "channel": script.channel or "",
        "original_text": script.original_text or "",
        "final_text": script.final_text or "",
        "stages": result,
    }


@router.post("/{script_id}/generate/{stage_name}")
def generate_stage(script_id: int, stage_name: str, db: Session = Depends(get_db)):
    """Generate a new attempt for a pipeline stage."""
    if stage_name not in STAGE_ORDER:
        return JSONResponse({"error": f"Invalid stage: {stage_name}"}, status_code=400)

    script = db.query(Script).get(script_id)
    if not script:
        return JSONResponse({"error": "Script not found"}, status_code=404)

    # Get accepted texts from previous stages for context
    context = _get_stage_context(db, script_id)

    # Check prerequisites
    stage_idx = STAGE_ORDER.index(stage_name)
    for prev_stage in STAGE_ORDER[:stage_idx]:
        if prev_stage not in context or not context[prev_stage]:
            return JSONResponse(
                {"error": f"Stage '{prev_stage}' must be accepted first"},
                status_code=400,
            )

    # Count existing attempts
    existing = db.query(PipelineStage).filter(
        PipelineStage.script_id == script_id,
        PipelineStage.stage_name == stage_name,
    ).count()

    # Create new attempt
    stage = PipelineStage(
        script_id=script_id,
        stage_name=stage_name,
        status="generating",
        attempt_number=existing + 1,
    )
    db.add(stage)
    db.commit()
    db.refresh(stage)
    stage_id = stage.id

    # Generate in background
    def _generate():
        gen_db = SessionLocal()
        try:
            from services.pipeline_generator import generate_stage as gen, get_stage_prompt
            gen_stage = gen_db.query(PipelineStage).get(stage_id)
            gen_script = gen_db.query(Script).get(script_id)

            # Build context for prompt
            gen_context = _get_stage_context(gen_db, script_id)
            host_info = get_host_info(gen_script.assigned_to)
            prompt_context = {
                "original_text": gen_script.original_text or "",
                "intro_text": gen_context.get("intro", ""),
                "part1_text": gen_context.get("part1", ""),
                "part2_text": gen_context.get("part2", ""),
                "part3_text": gen_context.get("part3", ""),
                **host_info,
            }

            prompt_template = get_stage_prompt(stage_name)
            gen_stage.prompt_used = prompt_template

            result_text = gen(stage_name, gen_script.original_text or "", prompt_context)
            gen_stage.result_text = result_text
            gen_stage.status = "draft"
            gen_db.commit()
            logger.info(f"Pipeline stage {stage_name} generated for script {script_id} (attempt {gen_stage.attempt_number})")
        except Exception as e:
            logger.error(f"Pipeline generation failed: {e}")
            try:
                gen_stage = gen_db.query(PipelineStage).get(stage_id)
                if gen_stage:
                    gen_stage.status = "failed"
                    gen_stage.result_text = f"Error: {str(e)[:500]}"
                    gen_db.commit()
            except Exception:
                pass
        finally:
            gen_db.close()

    executor.submit(_generate)

    return {"ok": True, "stage_id": stage_id, "attempt_number": existing + 1}


@router.post("/{script_id}/accept/{stage_name}/{attempt_id}")
def accept_stage(script_id: int, stage_name: str, attempt_id: int, db: Session = Depends(get_db)):
    """Accept a specific attempt for a stage."""
    stage = db.query(PipelineStage).get(attempt_id)
    if not stage or stage.script_id != script_id or stage.stage_name != stage_name:
        return JSONResponse({"error": "Stage attempt not found"}, status_code=404)

    # Reject all other attempts for this stage
    db.query(PipelineStage).filter(
        PipelineStage.script_id == script_id,
        PipelineStage.stage_name == stage_name,
        PipelineStage.id != attempt_id,
    ).update({"status": "rejected"})

    stage.status = "accepted"
    db.commit()

    # If accepting a previous stage, reset all subsequent stages
    stage_idx = STAGE_ORDER.index(stage_name)
    subsequent_stages = STAGE_ORDER[stage_idx + 1:]
    if subsequent_stages:
        db.query(PipelineStage).filter(
            PipelineStage.script_id == script_id,
            PipelineStage.stage_name.in_(subsequent_stages),
        ).delete(synchronize_session="fetch")
        # Also clear final text
        script = db.query(Script).get(script_id)
        if script:
            script.final_text = ""
            script.fact_check_report = ""
        db.commit()

    return {"ok": True}


@router.post("/{script_id}/fact-check")
def run_fact_check(script_id: int, db: Session = Depends(get_db)):
    """Run fact-checking on the accepted stages."""
    script = db.query(Script).get(script_id)
    if not script:
        return JSONResponse({"error": "Script not found"}, status_code=404)

    context = _get_stage_context(db, script_id)
    # Combine all accepted parts
    parts = [context.get(s, "") for s in STAGE_ORDER if context.get(s)]
    if not parts:
        return JSONResponse({"error": "No accepted stages to fact-check"}, status_code=400)

    combined_text = " ".join(parts)

    # Run fact-check
    from services.fact_checker import fact_check_script
    report = fact_check_script(combined_text)

    # Save report
    script.fact_check_report = json.dumps(report)
    db.commit()

    return {"ok": True, "report": report}


@router.post("/{script_id}/finalize")
def finalize_script(script_id: int, db: Session = Depends(get_db)):
    """Generate the final unified script using Claude."""
    script = db.query(Script).get(script_id)
    if not script:
        return JSONResponse({"error": "Script not found"}, status_code=404)

    context = _get_stage_context(db, script_id)
    # Check all stages accepted
    for stage_name in STAGE_ORDER:
        if not context.get(stage_name):
            return JSONResponse(
                {"error": f"Stage '{stage_name}' not accepted yet"},
                status_code=400,
            )

    # Build fact-check context
    fact_context = ""
    if script.fact_check_report:
        try:
            report = json.loads(script.fact_check_report)
            false_facts = [f for f in report.get("facts", []) if f.get("verdict") == "false"]
            if false_facts:
                fact_context = "FACT-CHECK CORRECTIONS (apply these):\n"
                for f in false_facts:
                    fact_context += f"- WRONG: {f['claim']}\n"
                    if f.get("correction"):
                        fact_context += f"  CORRECT: {f['correction']}\n"
        except (json.JSONDecodeError, TypeError):
            pass

    # Generate unified text
    from services.pipeline_generator import generate_stage
    host_info = get_host_info(script.assigned_to)
    enrichment_context = {
        "intro_text": context.get("intro", ""),
        "part1_text": context.get("part1", ""),
        "part2_text": context.get("part2", ""),
        "part3_text": context.get("part3", ""),
        "fact_check_context": fact_context,
        **host_info,
    }

    final_text = generate_stage("enrichment", script.original_text or "", enrichment_context)
    script.final_text = final_text
    # Also update modified_text for backward compatibility
    script.modified_text = final_text
    db.commit()

    return {"ok": True, "final_text": final_text}


@router.get("/{script_id}/stage-status/{stage_id}")
def get_stage_status(script_id: int, stage_id: int, db: Session = Depends(get_db)):
    """Poll status of a generating stage."""
    stage = db.query(PipelineStage).get(stage_id)
    if not stage or stage.script_id != script_id:
        return JSONResponse({"error": "Not found"}, status_code=404)
    return {
        "id": stage.id,
        "status": stage.status,
        "result_text": stage.result_text,
        "attempt_number": stage.attempt_number,
    }


@router.put("/prompts/{stage_name}")
def save_stage_prompt(stage_name: str, body: dict, db: Session = Depends(get_db)):
    """Save a pipeline stage prompt permanently."""
    key = f"pipeline_{stage_name}"
    value = body.get("value", "")
    if not value:
        return JSONResponse({"error": "Prompt value required"}, status_code=400)

    existing = db.query(SystemPrompt).filter(SystemPrompt.key == key).first()
    if existing:
        existing.value = value
    else:
        db.add(SystemPrompt(key=key, value=value))
    db.commit()
    return {"ok": True}


@router.get("/prompts/{stage_name}")
def get_stage_prompt_api(stage_name: str):
    """Get the current prompt for a stage."""
    from services.pipeline_generator import get_stage_prompt, DEFAULT_PROMPTS
    current = get_stage_prompt(stage_name)
    default = DEFAULT_PROMPTS.get(stage_name, "")
    return {
        "stage_name": stage_name,
        "prompt": current,
        "is_custom": current != default,
        "default": default,
    }


@router.get("/{script_id}/export-word")
def export_pipeline_word(script_id: int, db: Session = Depends(get_db)):
    """Export script as Word document."""
    script = db.query(Script).get(script_id)
    if not script:
        return JSONResponse({"error": "Script not found"}, status_code=404)

    from models import Video
    video = db.query(Video).get(script.video_id) if script.video_id else None

    from services.word_export import generate_script_docx
    buffer = generate_script_docx(script, video)

    filename = f"script_{script_id}.docx"
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _get_stage_context(db: Session, script_id: int) -> dict:
    """Get accepted text for each stage."""
    stages = db.query(PipelineStage).filter(
        PipelineStage.script_id == script_id,
        PipelineStage.status == "accepted",
    ).all()
    return {s.stage_name: s.result_text for s in stages}
