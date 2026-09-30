"""Export OpenAPI and schema-validated documentation fixtures, without providers."""
import json
from solvo_client_agent.api.app import create_app
from .contract_samples import ROOT, examples


def main():
    destination = ROOT / "docs/contracts"
    (destination / "examples").mkdir(parents=True, exist_ok=True)
    for name, model in examples().items():
        data = model.model_dump(mode="json")
        type(model).model_validate(data)
        (destination / "examples" / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    (destination / "application-api-v1.openapi.json").write_text(json.dumps(create_app().openapi(), ensure_ascii=False, indent=2) + "\n")
    print(f"Exported {len(examples())} validated examples and OpenAPI.")


if __name__ == "__main__":
    main()
