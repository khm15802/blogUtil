import json
import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .models import PostData


class PostRenderer:
    def __init__(self, template_dir: Path | None = None):
        template_dir = template_dir or Path(__file__).parent / "templates"
        self.environment = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(("html", "xml")),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(self, post: PostData) -> str:
        template = self.environment.get_template("post.html.j2")
        return template.render(post=post, image_for=post.image_by_slot)

    def export(self, post: PostData, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        images_dir = output_dir / "images"
        images_dir.mkdir(exist_ok=True)

        for image in post.images:
            if not image.local_path:
                continue
            source = Path(image.local_path)
            if source.is_file():
                shutil.copy2(source, images_dir / image.filename)

        html_path = output_dir / "post.html"
        html_path.write_text(self.render(post), encoding="utf-8")
        (output_dir / "post-data.json").write_text(
            json.dumps(post.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return html_path
