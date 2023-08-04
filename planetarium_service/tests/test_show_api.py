import os
import tempfile

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from PIL import Image
from rest_framework import status
from rest_framework.test import APIClient

from planetarium_service.models import (
    AstronomyShow,
    PlanetariumDome,
    ShowSession,
    ShowTheme
)
from planetarium_service.serializers import (
    AstronomyShowDetailSerializer,
    AstronomyShowListSerializer
)

SHOW_URL = reverse("planetarium_service:astronomyshow-list")
SHOW_SESSION_URL = reverse("planetarium_service:showsession-list")


def sample_show(**params):
    defaults = {
        "title": "Sample show",
        "description": "Sample description",
    }
    defaults.update(params)

    return AstronomyShow.objects.create(**defaults)


def sample_show_session(**params):
    planetarium_dome = PlanetariumDome.objects.create(
        name="Blue", rows=20, seats_in_row=20
    )

    defaults = {
        "datetime": "2022-06-02 14:00:00",
        "astronomy_show": None,
        "planetarium_dome": planetarium_dome,
    }
    defaults.update(params)

    return ShowSession.objects.create(**defaults)


def image_upload_url(astronomy_show_id):
    return reverse("planetarium_service:astronomyshow-upload-image", args=[astronomy_show_id])


def detail_url(astronomy_show_id):
    return reverse("planetarium_service:astronomyshow-detail", args=[astronomy_show_id])


class UnauthenticatedAstronomyShowApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(SHOW_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "testpass",
        )
        self.client.force_authenticate(self.user)

    def test_list_shows(self):
        sample_show()
        sample_show()

        res = self.client.get(SHOW_URL)

        shows = AstronomyShow.objects.order_by("id")
        serializer = AstronomyShowListSerializer(shows, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_shows_by_themes(self):
        theme1 = ShowTheme.objects.create(name="Theme 1")
        theme2 = ShowTheme.objects.create(name="Theme 2")

        show1 = sample_show(title="Show 1")
        show2 = sample_show(title="Show 2")

        show1.themes.add(theme1)
        show2.themes.add(theme2)

        show3 = sample_show(title="Show without themes")

        res = self.client.get(
            SHOW_URL, {"themes": f"{theme1.id},{theme2.id}"}
        )

        serializer1 = AstronomyShowListSerializer(show1)
        serializer2 = AstronomyShowListSerializer(show2)
        serializer3 = AstronomyShowListSerializer(show3)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_filter_shows_by_title(self):
        show1 = sample_show(title="Show")
        show2 = sample_show(title="Another Show")
        show3 = sample_show(title="No match")

        res = self.client.get(SHOW_URL, {"title": "Show"})

        serializer1 = AstronomyShowListSerializer(show1)
        serializer2 = AstronomyShowListSerializer(show2)
        serializer3 = AstronomyShowListSerializer(show3)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_retrieve_show_detail(self):
        show = sample_show()
        show.themes.add(ShowTheme.objects.create(name="Theme"))

        url = detail_url(show.id)
        res = self.client.get(url)

        serializer = AstronomyShowDetailSerializer(show)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_show_forbidden(self):
        payload = {
            "title": "Show",
            "description": "Description",
        }
        res = self.client.post(SHOW_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@admin.com", "testpass", is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_show(self):
        payload = {
            "title": "Show",
            "description": "Description",
        }
        res = self.client.post(SHOW_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        show = AstronomyShow.objects.get(id=res.data["id"])
        for key in payload.keys():
            self.assertEqual(payload[key], getattr(show, key))

    def test_create_show_with_genres(self):
        theme1 = ShowTheme.objects.create(name="Moon")
        theme2 = ShowTheme.objects.create(name="Solar system")
        payload = {
            "title": "Why are planets round?",
            "themes": [theme1.id, theme2.id],
            "description": "With Spider-Man's identity now revealed, Peter asks Doctor Strange for help.",
        }
        res = self.client.post(SHOW_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        show = AstronomyShow.objects.get(id=res.data["id"])
        themes = show.themes.all()
        self.assertEqual(themes.count(), 2)
        self.assertIn(theme1, themes)
        self.assertIn(theme2, themes)


class ShowImageUploadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.show = sample_show()
        self.movie_session = sample_show_session(astronomy_show=self.show)

    def tearDown(self):
        self.show.image.delete()

    def test_upload_image_to_show(self):
        url = image_upload_url(self.show.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")
        self.show.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(os.path.exists(self.show.image.path))

    def test_upload_image_bad_request(self):
        url = image_upload_url(self.show.id)
        res = self.client.post(url, {"image": "not image"}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_image_to_show_list_should_not_work(self):
        url = SHOW_URL
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(
                url,
                {
                    "title": "Title",
                    "description": "Description",
                    "image": ntf,
                },
                format="multipart",
            )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        show = AstronomyShow.objects.get(title="Title")

    def test_image_url_is_shown_on_show_detail(self):
        url = image_upload_url(self.show.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(detail_url(self.show.id))

        self.assertIn("image", res.data)

    def test_image_url_is_shown_on_movie_list(self):
        url = image_upload_url(self.show.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(SHOW_URL)

        self.assertIn("image", res.data[0].keys())

    def test_image_url_is_shown_on_show_session_detail(self):
        url = image_upload_url(self.show.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(SHOW_SESSION_URL)

        self.assertIn("show_image", res.data[0].keys())

    def test_put_show_not_allowed(self):
        payload = {
            "title": "New show",
            "description": "New description",
        }

        show = sample_show()
        url = detail_url(show.id)

        res = self.client.put(url, payload)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_show_not_allowed(self):
        show = sample_show()
        url = detail_url(show.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
