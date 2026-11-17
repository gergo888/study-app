import shutil
import tempfile
from pathlib import Path

from django.http import Http404
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.content import repository, sync
from apps.core import tables
from apps.core.files import safe_join, serve_file
from apps.core.paths import chapter_dir, figures_dir
from apps.study import plan as plan_service

from . import outline, pdf, services


def material_json(m: tables.MaterialRow) -> dict:
    chapters = services.material_chapters(m.slug)
    counts = {s: 0 for s in services.STATUSES}
    for c in chapters:
        counts[c.status] = counts.get(c.status, 0) + 1
    return {
        "slug": m.slug,
        "title": m.title,
        "description": m.description,
        "has_pdf": bool(m.pdf_path),
        "pdf_name": m.pdf_name,
        "page_count": m.page_count,
        "chapter_level": m.chapter_level,
        "chapters_total": len(chapters),
        "status_counts": counts,
        "plan": {
            "start": m.plan_start.isoformat() if m.plan_start else None,
            "target": m.plan_target.isoformat() if m.plan_target else None,
            "weekdays": [int(d) for d in m.study_weekdays.split(",") if d.strip()],
        },
        "created_at": m.created_at.isoformat(),
    }


def chapter_json(c: tables.ChapterRow, *, plan_date: str | None = None) -> dict:
    docs = {k: repository.doc_path(c.material, c.key, k).exists() for k in ("summary", "flashcards", "quiz")}
    return {
        "material": c.material,
        "key": c.key,
        "order": c.order,
        "code": c.code,
        "title": c.title,
        "group_title": c.group_title,
        "group_subtitle": c.group_subtitle,
        "start_page": c.start_page,
        "end_page": c.end_page,
        "pages": c.end_page - c.start_page + 1,
        "status": c.status,
        "read_at": c.read_at.isoformat() if c.read_at else None,
        "learned_at": c.learned_at.isoformat() if c.learned_at else None,
        "learned_via": c.learned_via,
        "has_content": docs["summary"],
        "docs": docs,
        "scheduled_date": plan_date,
    }


class MaterialCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(max_length=2000, required=False, allow_blank=True, default="")


class MaterialListView(APIView):
    def get(self, request):
        rows = sorted(tables.materials.all(), key=lambda m: m.created_at)
        return Response([material_json(m) for m in rows])

    def post(self, request):
        ser = MaterialCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        m = services.create_material(ser.validated_data["title"], ser.validated_data["description"])
        return Response(material_json(m), status=status.HTTP_201_CREATED)


class MaterialDetailView(APIView):
    def get(self, request, slug):
        m = services.get_material(slug)
        plan = plan_service.plan_status(slug)
        chapters = [chapter_json(c, plan_date=plan["items"].get(c.key)) for c in services.material_chapters(slug)]
        return Response({**material_json(m), "chapters": chapters, "plan_status": {k: v for k, v in plan.items() if k != "items"}})

    def patch(self, request, slug):
        ser = MaterialCreateSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        m = services.update_material(slug, **{k: v for k, v in ser.validated_data.items()})
        return Response(material_json(m))

    def delete(self, request, slug):
        services.delete_material(slug)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MaterialPdfView(APIView):
    def get(self, request, slug):
        m = services.get_material(slug)
        if not m.pdf_path:
            raise Http404("no PDF")
        return serve_file(pdf.pdf_path(m), download_name=m.pdf_name or f"{slug}.pdf")

    def post(self, request, slug):
        services.get_material(slug)
        upload = request.FILES.get("file")
        if upload is None:
            return Response({"detail": "Send the PDF as multipart field 'file'."}, status=400)
        if not upload.name.lower().endswith(".pdf"):
            return Response({"detail": "Only PDF files are supported."}, status=400)
        level = request.data.get("level")
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            for chunk in upload.chunks():
                tmp.write(chunk)
            tmp_path = Path(tmp.name)
        try:
            with open(tmp_path, "rb") as fh:
                if fh.read(5) != b"%PDF-":
                    return Response({"detail": "The file is not a PDF."}, status=400)
            m = services.attach_pdf(slug, tmp_path, upload.name, move=True, level=int(level) if level else None)
        finally:
            tmp_path.unlink(missing_ok=True)
        return Response(material_json(m), status=status.HTTP_201_CREATED)


class MaterialOutlineView(APIView):
    def get(self, request, slug):
        m = services.get_material(slug)
        toc, pages = services.material_toc(m)
        return Response(
            {
                "levels": outline.level_stats(toc, pages),
                "suggested_level": outline.suggest_level(toc, pages) if toc else None,
                "current_level": m.chapter_level,
                "tree": outline.outline_tree(toc),
            }
        )


class BuildChaptersView(APIView):
    def post(self, request, slug):
        level = int(request.data.get("level") or 0)
        if level < 1:
            return Response({"detail": "level must be >= 1"}, status=400)
        rows = services.build_chapters(slug, level)
        return Response({"chapters": len(rows)})


class ChapterStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=services.STATUSES)


class ChapterDetailView(APIView):
    def get(self, request, slug, key):
        m = services.get_material(slug)
        c = services.get_chapter(slug, key)
        sync.ensure_indexed(slug, key)
        chapters = services.material_chapters(slug)
        idx = next(i for i, x in enumerate(chapters) if x.key == key)
        health = sync.chapter_health(slug, key)
        points = [p for p in tables.points.filter(material=slug, chapter=key) if not p.archived]
        cards = [r for r in tables.cards.filter(material=slug, chapter=key) if not r.archived]
        plan = plan_service.plan_status(slug)
        return Response(
            {
                **chapter_json(c, plan_date=plan["items"].get(key)),
                "material_title": m.title,
                "prev": chapters[idx - 1].key if idx > 0 else None,
                "next": chapters[idx + 1].key if idx + 1 < len(chapters) else None,
                "pdf_url": f"/api/chapters/{slug}/{key}/pdf/",
                "counts": {
                    "points": len(points),
                    "flashcards": sum(1 for r in cards if r.kind == "flashcard"),
                    "quiz": sum(1 for r in cards if r.kind == "quiz"),
                    "stale": len(health.stale),
                    "missing": len(health.missing),
                },
                "health": health.as_dict(),
            }
        )

    def patch(self, request, slug, key):
        ser = ChapterStatusSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        c = services.set_chapter_status(slug, key, ser.validated_data["status"], via="manual")
        return Response(chapter_json(c))


class ChapterPdfView(APIView):
    def get(self, request, slug, key):
        m = services.get_material(slug)
        c = services.get_chapter(slug, key)
        if not m.pdf_path:
            raise Http404("no PDF")
        path = pdf.chapter_slice(m, c)
        return serve_file(path, download_name=f"{slug}-{key}.pdf")


class ChapterFileView(APIView):
    """Figures referenced by the Markdown (figures/...) and candidates (_source/figures/...)."""

    def get(self, request, slug, key, path):
        services.get_chapter(slug, key)
        if not (path.startswith("figures/") or path.startswith("_source/figures/")):
            raise Http404("not a figure")
        return serve_file(safe_join(chapter_dir(slug, key), path))


class FiguresView(APIView):
    def get(self, request, slug, key):
        services.get_chapter(slug, key)
        folder = figures_dir(slug, key)
        adopted = sorted(p.name for p in folder.glob("*") if p.is_file()) if folder.exists() else []
        candidates = pdf.load_candidates(slug, key)
        by_name = {Path(c["file"]).name: c for c in candidates}
        return Response(
            {
                "adopted": [
                    {
                        "path": f"figures/{name}",
                        "url": f"/api/chapters/{slug}/{key}/files/figures/{name}",
                        "caption": by_name.get(name, {}).get("caption", ""),
                        "page": by_name.get(name, {}).get("page"),
                    }
                    for name in adopted
                ],
                "candidates": [
                    {**c, "url": f"/api/chapters/{slug}/{key}/files/{c['file']}", "adopted": Path(c["file"]).name in adopted}
                    for c in candidates
                ],
            }
        )

    def post(self, request, slug, key):
        """{"action": "adopt", "key": "<candidate key>"} or {"action": "extract"}."""
        m = services.get_material(slug)
        c = services.get_chapter(slug, key)
        action = request.data.get("action")
        if action == "extract":
            found = pdf.extract_figures(m, c)
            return Response({"candidates": len(found)})
        if action == "adopt":
            cand = next((x for x in pdf.load_candidates(slug, key) if x["key"] == request.data.get("key")), None)
            if cand is None:
                raise Http404("unknown candidate")
            src = safe_join(chapter_dir(slug, key), cand["file"])
            dest = figures_dir(slug, key) / Path(cand["file"]).name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest)
            return Response({"path": f"figures/{dest.name}", "url": f"/api/chapters/{slug}/{key}/files/figures/{dest.name}", "caption": cand.get("caption", "")})
        return Response({"detail": "action must be adopt or extract"}, status=400)
