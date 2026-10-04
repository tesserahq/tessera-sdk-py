from tessera_sdk.mcp import check_provider_contract, load_contract_fixture

TOOLS = [
    {
        "name": "create_person",
        "outputSchema": {"type": "object", "required": ["id"]},
    }
]
NORMAL_RESULT = {
    "content": [{"type": "text", "text": '{"id":"person-123"}'}],
    "structuredContent": {"id": "person-123"},
    "isError": False,
}


def test_provider_contract_accepts_additive_valid_metadata():
    result = {**NORMAL_RESULT, "_meta": load_contract_fixture("valid_metadata.json")}

    report = check_provider_contract(
        tools_before=TOOLS,
        tools_after=TOOLS,
        results_before={"create_person": NORMAL_RESULT},
        results_after={"create_person": result},
    )

    assert report.compliant


def test_provider_contract_reports_output_schema_change():
    changed = [{"name": "create_person", "outputSchema": {"type": "string"}}]

    report = check_provider_contract(tools_before=TOOLS, tools_after=changed)

    assert [item.code for item in report.violations] == ["output_schema_changed"]


def test_provider_contract_reports_normal_result_change():
    changed_result = {**NORMAL_RESULT, "structuredContent": {"id": "different"}}

    report = check_provider_contract(
        tools_before=TOOLS,
        tools_after=TOOLS,
        results_before={"create_person": NORMAL_RESULT},
        results_after={"create_person": changed_result},
    )

    assert [item.code for item in report.violations] == ["normal_result_changed"]


def test_provider_contract_reports_invalid_metadata_without_raising():
    result = {**NORMAL_RESULT, "_meta": {"events": []}}

    report = check_provider_contract(
        tools_before=TOOLS,
        tools_after=TOOLS,
        results_after={"create_person": result},
    )

    assert [item.code for item in report.violations] == ["invalid_metadata"]
