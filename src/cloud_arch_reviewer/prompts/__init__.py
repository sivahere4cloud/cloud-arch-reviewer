from importlib.resources import files


def load_prompt(name: str) -> str:
    prompt_file = files("cloud_arch_reviewer.prompts").joinpath(name)
    text = prompt_file.read_text(encoding="utf-8")
    return text