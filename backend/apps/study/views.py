
from django.http import Http404
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.content import repository, serializers as out, sync
from apps.core import tables
from apps.core.csvstore import utcnow
from apps.materials import services as material_services

from . import plan as plan_service
from . import services, srs, stats

MODES = ("flashcards", "quiz", "write")


def _chapter_items(slug: str, key: str, mode: str, point_filter: set[str] | None) -> list[dict]:
    sync.ensure_indexed(slug, key)
    chapter = material_services.get_chapter(slug, key)
    summary = repository.load(slug, key, "summary").doc
    if summary is None:
        return []
    points = {p.key: (s, p) for s, p in summary.all_points()}
    order = {k: i for i, k in enumerate(points)}
    base = {"material": slug, "chapter": key, "chapter_title": chapter.title}

    def point_info(pk: str) -> dict:
        s_p = points.get(pk)
        if not s_p:
            return {"point_title_en": pk, "point_title_hu": pk, "section_en": "", "section_hu": ""}
        s, p = s_p
        return {"point_title_en": p.title_en, "point_title_hu": p.title_hu, "section_en": s.heading_en, "section_hu": s.heading_hu}

    items: list[dict] = []
    if mode == "write":
        for pk, (s, p) in points.items():
            if point_filter is None or pk in point_filter:
                items.append({**base, "kind": "write", "key": pk, "point_key": pk, **point_info(pk), "data": out.point_json(slug, key, p)})
        return items

    kind = "flashcards" if mode == "flashcards" else "quiz"
    card_kind = "flashcard" if mode == "flashcards" else "quiz"
    doc = repository.load(slug, key, kind).doc
    if doc is None:
        return []
    states = out.card_states(slug, key, card_kind)
    entries = doc.cards if kind == "flashcards" else doc.questions
    for e in sorted(entries, key=lambda e: order.get(e.point_key, 10**6)):
        if point_filter is not None and e.point_key not in point_filter:
            continue
        data = (out.flashcard_json if kind == "flashcards" else out.question_json)(slug, key, e, states.get(e.key))
        items.append({**base, "kind": card_kind, "key": e.key, "point_key": e.point_key, **point_info(e.point_key), "data": data})
    return items


class PracticeSessionView(APIView):
    """GET ?mode=flashcards|quiz|write&material=&chapter=&points=a,b  or  ?due=1[&material=]"""

    def get(self, request):
        q = request.query_params
        if q.get("due") in ("1", "true"):
            now = utcnow()
            material = q.get("material")
            due = [c for c in tables.cards.all() if srs.is_due(c, now) and (not material or c.material == material)]
            due.sort(key=lambda c: c.due)
            limit = int(q.get("limit") or 100)
            items = []
            cache: dict = {}
            for c in due[:limit]:
                ck = (c.material, c.chapter, c.kind)
                if ck not in cache:
                    cache[ck] = {
                        i["key"]: i
                        for i in _chapter_items(c.material, c.chapter, "flashcards" if c.kind == "flashcard" else "quiz", None)
                    }
                item = cache[ck].get(c.card_key)
                if item:
                    items.append(item)
            return Response({"mode": "review", "items": items})

        mode = q.get("mode")
        if mode not in MODES:
            return Response({"detail": f"mode must be one of {MODES}"}, status=400)
        slug, key = q.get("material"), q.get("chapter")
        if not slug or not key:
            return Response({"detail": "material and chapter are required"}, status=400)
        points = {p for p in (q.get("points") or "").split(",") if p} or None
        return Response({"mode": mode, "items": _chapter_items(slug, key, mode, points)})


class AnswerSerializer(serializers.Serializer):
    material = serializers.CharField()
    chapter = serializers.CharField()
    kind = serializers.ChoiceField(choices=["flashcard", "quiz"])
    card_key = serializers.CharField()
    rating = serializers.IntegerField(required=False, min_value=1, max_value=4)
    selected_index = serializers.IntegerField(required=False, min_value=0, max_value=3)
    context = serializers.ChoiceField(choices=["learn", "review"], default="learn")


class AnswerView(APIView):
    def post(self, request):
        ser = AnswerSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        v = ser.validated_data
        slug, key = v["material"], v["chapter"]
        material_services.get_chapter(slug, key)
        sync.ensure_indexed(slug, key)
        correct_index = None
        if v["kind"] == "quiz":
            doc = repository.load(slug, key, "quiz").doc
            q = next((x for x in (doc.questions if doc else []) if x.key == v["card_key"]), None)
            if q is None:
                raise Http404("question not found")
            correct_index = q.correct_index
        try:
            result = services.record_answer(
                slug,
                key,
                v["kind"],
                v["card_key"],
                rating=v.get("rating"),
                selected_index=v.get("selected_index"),
                correct_index=correct_index,
                context=v["context"],
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        result["correct_index"] = correct_index
        return Response(result)


class PlanSerializer(serializers.Serializer):
    start_date = serializers.DateField(required=False)
    target_date = serializers.DateField(required=False, allow_null=True)
    weekdays = serializers.ListField(child=serializers.IntegerField(min_value=0, max_value=6), required=False)


class PlanView(APIView):
    def get(self, request, slug):
        material_services.get_material(slug)
        return Response(plan_service.plan_status(slug))

    def post(self, request, slug):
        material_services.get_material(slug)
        ser = PlanSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        v = ser.validated_data
        try:
            plan_service.generate(
                slug,
                v.get("start_date") or plan_service.today(),
                v.get("target_date"),
                set(v.get("weekdays") or range(7)),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(plan_service.plan_status(slug))


class DashboardView(APIView):
    def get(self, request):
        data = stats.dashboard()
        nexts = []
        for m in tables.materials.all():
            st = plan_service.plan_status(m.slug)
            if st["next_chapter"]:
                c = material_services.get_chapter(m.slug, st["next_chapter"])
                nexts.append(
                    {
                        "material": m.slug,
                        "material_title": m.title,
                        "chapter": c.key,
                        "code": c.code,
                        "title": c.title,
                        "status": c.status,
                        "scheduled_date": st["items"].get(c.key),
                        "behind": st["behind"],
                        "learned": st["learned"],
                        "total": st["total"],
                    }
                )
        data["continue"] = nexts
        data["today"] = plan_service.today().isoformat()
        return Response(data)
