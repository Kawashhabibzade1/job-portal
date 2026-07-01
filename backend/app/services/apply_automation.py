from app.models import ApplyAutomationRequest, ApplyAutomationResponse, UserProfile


def prepare_apply_automation(
    payload: ApplyAutomationRequest,
    fallback_profile: UserProfile,
) -> ApplyAutomationResponse:
    profile = payload.profile or fallback_profile
    fields = {
        "target_role": payload.job.title,
        "company": payload.job.company or "",
        "skills": ", ".join(profile.skills),
        "languages": ", ".join(profile.languages),
        "cv_summary": profile.cv_summary[:1200],
    }
    apply_url = payload.job.apply_url or payload.job.source_url or ""
    if not apply_url:
        return ApplyAutomationResponse(
            status="blocked",
            message="This job does not include an application URL, so I cannot open an external portal.",
            fields=fields,
            apply_url="",
            confirmation_required=True,
        )
    if not payload.confirm_submit:
        return ApplyAutomationResponse(
            status="needs_confirmation",
            message=(
                "I prepared the application fields. Confirm before I attempt any external portal action. "
                "I will not submit automatically."
            ),
            fields=fields,
            apply_url=apply_url,
            confirmation_required=True,
        )
    return ApplyAutomationResponse(
        status="prepared",
        message=(
            "Confirmation received. Browser portal automation is prepared, but final submission remains manual "
            "until portal-specific automation is approved and verified."
        ),
        fields=fields,
        apply_url=apply_url,
        confirmation_required=True,
    )
