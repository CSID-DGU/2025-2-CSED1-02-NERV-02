from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

router = APIRouter()


class AITrainingRequest(BaseModel):
    module_name: str = Field(..., examples=["sexual"])
    text: str = Field(..., min_length=1, examples=["실시간 학습할 댓글 내용"])
    label: int = Field(..., ge=0, le=1, examples=[1])
    save: bool = Field(default=True)

    @field_validator("module_name")
    @classmethod
    def normalize_module_name(cls, value: str) -> str:
        value = value.strip().lower()

        if not value:
            raise ValueError("module_name은 비어 있을 수 없습니다.")

        return value

class AITrainingResponse(BaseModel):
    module: str
    loss: float
    score_after_step: float
    saved: bool

@router.post("/train-one", response_model=AITrainingResponse, summary="AI 모듈 실시간 단일 학습")
async def train_ai_module_one(
    request: Request,
    payload: AITrainingRequest,
):
    """
    실행 중인 attention head 모듈을 단일 샘플로 즉시 업데이트합니다.

    - module_name: sexual, spam, pii, criticism, politics, basic, family 등
    - label: 0 = normal, 1 = positive
    - save: true이면 업데이트된 attention_head.pt를 저장합니다.
    """
    second_pass_filter = getattr(request.app.state, "second_pass_filter", None)

    if second_pass_filter is None:
        raise HTTPException(
            status_code=503,
            detail="SecondPassFilter가 초기화되지 않았습니다.",
        )

    try:
        result = await second_pass_filter.update_ai_module(
            module_name=payload.module_name,
            text=payload.text,
            label=payload.label,
            save=payload.save,
        )

        return AITrainingResponse(
            module=result["module"],
            loss=result["loss"],
            score_after_step=result["score_after_step"],
            saved=payload.save,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"AI 실시간 학습 중 오류가 발생했습니다: {e}",
        )