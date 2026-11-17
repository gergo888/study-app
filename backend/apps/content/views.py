from django.http import Http404
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.materials import services as material_services
from apps.study import services as study_services

from . import notes as notes_service
from . import ops, repository, serializers as out, sync
from .answer_check import check_answer
from .mdformat import validate

DOC_KINDS = ("summary", "flashcards", "quiz", "notes")


def _chapter(slug: str, key: str):
    chapter = material_services.get_chapter(slug, key)
    sync.ensure_indexed(slug, key)
    return chapter


def _issues(loaded) -> list[dict]:
    return [i.as_dict() for i in loaded.issues]


def _run(fn):
    try:
        return fn()
    except ops.OpError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class SummaryView(APIView):
    def get(self, request, slug, key):
        _chapter(slug, key)
        loaded = repository.load(slug, key, "summary")
        health = sync.chapter_health(slug, key)
        progress = study_services.point_progress(slug, key)
        fc = repository.load(slug, key, "flashcards")
        qz = repository.load(slug, key, "quiz")
        link_issues = validate.validate_links(loaded.doc, fc.doc, qz.doc) if loaded.doc else []
        sections = []
        if loaded.doc:
            for s in loaded.doc.sections:
                sections.append(
                    {
                        "key": s.key,
                        "heading_en": s.heading_en,
                        "heading_hu": s.heading_hu,
                        "points": [
                            {
                                **out.point_json(slug, key, p),
                                "stale": p.key in health.stale_points,
                                "missing": health.missing.get(p.key, []),
                                "progress": progress.get(p.key, {}),
                            }
                            for p in s.points
                        ],
                    }
                )
        return Response(
            {
                "exists": loaded.exists,
                "sha": loaded.sha,
                "meta": loaded.doc.meta if loaded.doc else {},
                "sections": sections,
                "issues": _issues(loaded) + [i.as_dict() for i in link_issues],
                "health": health.as_dict(),
            }
        )

    def post(self, request, slug, key):
        _chapter(slug, key)
        data = request.data
        return _run(lambda: Response(ops.summary_op(slug, key, data.get("op", ""), data, data.get("base_sha"))))


class CardsView(APIView):
    """kind = flashcards | quiz"""

    def get(self, request, slug, key, kind):
        if kind not in ("flashcards", "quiz"):
            raise Http404()
        _chapter(slug, key)
        loaded = repository.load(slug, key, kind)
        card_kind = "flashcard" if kind == "flashcards" else "quiz"
        states = out.card_states(slug, key, card_kind)
        stale = {s["card_key"] for s in sync.chapter_health(slug, key).stale if s["kind"] == card_kind}
        items = []
        if loaded.doc:
            if kind == "flashcards":
                items = [out.flashcard_json(slug, key, c, states.get(c.key), c.key in stale) for c in loaded.doc.cards]
            else:
                items = [out.question_json(slug, key, q, states.get(q.key), q.key in stale) for q in loaded.doc.questions]
        return Response({"exists": loaded.exists, "sha": loaded.sha, "items": items, "issues": _issues(loaded)})

    def post(self, request, slug, key, kind):
        if kind not in ("flashcards", "quiz"):
            raise Http404()
        _chapter(slug, key)
        data = request.data
        return _run(lambda: Response(ops.card_op(slug, key, kind, data.get("op", ""), data, data.get("base_sha"))))


class ConfirmCardView(APIView):
    """Mark a stale card as still valid for the current point text."""

    def post(self, request, slug, key):
        _chapter(slug, key)
        kind = request.data.get("kind")
        if kind not in ("flashcard", "quiz"):
            return Response({"detail": "kind must be flashcard or quiz"}, status=400)
        sync.confirm_card(slug, key, kind, request.data.get("card_key", ""))
        return Response({"ok": True})


class RawDocumentSerializer(serializers.Serializer):
    text = serializers.CharField(allow_blank=True, trim_whitespace=False, max_length=2_000_000)
    base_sha = serializers.CharField(allow_blank=True, allow_null=True, required=False)


class RawDocumentView(APIView):
    def get(self, request, slug, key, kind):
        if kind not in DOC_KINDS:
            raise Http404()
        _chapter(slug, key)
        loaded = repository.load(slug, key, kind)
        return Response({"exists": loaded.exists, "sha": loaded.sha, "text": loaded.text, "issues": _issues(loaded)})

    def put(self, request, slug, key, kind):
        if kind not in DOC_KINDS:
            raise Http404()
        chapter = _chapter(slug, key)
        ser = RawDocumentSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        text = ser.validated_data["text"]
        if kind == "notes" and not text.startswith("---"):
            text = f"---\ntitle: Notes · {chapter.title}\n---\n\n{text}"
        sha = repository.write_text(slug, key, kind, text, ser.validated_data.get("base_sha") or None)
        loaded = repository.load(slug, key, kind)
        return Response({"sha": sha, "issues": _issues(loaded)})


class CheckAnswerView(APIView):
    def post(self, request, slug, key, point_key):
        _chapter(slug, key)
        loaded = repository.load(slug, key, "summary")
        found = loaded.doc.find_point(point_key) if loaded.doc else None
        if found is None:
            raise Http404("point not found")
        _, point = found
        lang = request.data.get("lang", "en")
        result = check_answer(str(request.data.get("text", "")), point.concepts)
        result["original"] = point.body_hu if lang == "hu" else point.body_en
        return Response(result)


class PointActivityView(APIView):
    def post(self, request, slug, key, point_key):
        _chapter(slug, key)
        try:
            res = study_services.record_point_activity(
                slug, key, point_key, request.data.get("kind", ""), request.data.get("result", ""), request.data.get("context", "learn")
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(res)


class NoteSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200, allow_blank=True, required=False, default="")
    body = serializers.CharField(allow_blank=True, trim_whitespace=False, required=False, default="", max_length=1_000_000)
    base_sha = serializers.CharField(required=False, allow_blank=True, default="")


class NotesView(APIView):
    def get(self, request, slug):
        material_services.get_material(slug)
        return Response(notes_service.list_notes(slug))

    def post(self, request, slug):
        material_services.get_material(slug)
        ser = NoteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        note = notes_service.create_note(slug, ser.validated_data["title"], ser.validated_data["body"])
        return Response(note, status=status.HTTP_201_CREATED)


class NoteDetailView(APIView):
    def get(self, request, slug, note_id):
        material_services.get_material(slug)
        return Response(notes_service.get_note(slug, note_id))

    def put(self, request, slug, note_id):
        material_services.get_material(slug)
        ser = NoteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        v = ser.validated_data
        return Response(notes_service.update_note(slug, note_id, v["title"], v["body"], v["base_sha"]))

    def delete(self, request, slug, note_id):
        material_services.get_material(slug)
        notes_service.delete_note(slug, note_id)
        return Response(status=status.HTTP_204_NO_CONTENT)
