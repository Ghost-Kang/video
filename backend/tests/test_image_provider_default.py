"""B6/D1 — image-gen provider default must be domestic (Apimart), per PIPL §38.

The default was "google" (Gemini, cross-border). 改写已隔离境内 doubao; the image
leg processing real Beta user data must not silently go cross-border. These tests
lock the compliance red line: with no env override, the provider resolves to
Apimart, and the cross-border path requires an explicit IMAGE_GEN_PROVIDER=google.

Hermetic: GoogleProvider.__init__ builds a real genai.Client, so we stub both
provider classes to avoid network / credentials.
"""

from __future__ import annotations

import importlib

import pytest


def test_config_default_is_domestic(monkeypatch):
    """No env → config.IMAGE_GEN_PROVIDER == 'apimart' (compliance red line)."""
    monkeypatch.delenv("IMAGE_GEN_PROVIDER", raising=False)
    import agent.config as config

    importlib.reload(config)
    try:
        assert config.IMAGE_GEN_PROVIDER == "apimart"
    finally:
        importlib.reload(config)  # restore ambient


def test_get_provider_defaults_to_apimart(monkeypatch):
    import agent.tools.generation as gen

    monkeypatch.setattr(gen, "IMAGE_GEN_PROVIDER", "apimart")
    monkeypatch.setattr(gen, "ApimartProvider", lambda: "APIMART")
    monkeypatch.setattr(gen, "GoogleProvider", lambda: "GOOGLE")
    assert gen.get_provider() == "APIMART"


def test_get_provider_google_only_when_explicit(monkeypatch):
    import agent.tools.generation as gen

    monkeypatch.setattr(gen, "IMAGE_GEN_PROVIDER", "google")
    monkeypatch.setattr(gen, "ApimartProvider", lambda: "APIMART")
    monkeypatch.setattr(gen, "GoogleProvider", lambda: "GOOGLE")
    assert gen.get_provider() == "GOOGLE"


def test_execute_node_falls_back_to_config_provider(monkeypatch, tmp_path):
    """execute_node default is None → must fall back to config.IMAGE_GEN_PROVIDER,
    not a hardcoded 'google' (the second cross-border drift the verify pass found)."""
    monkeypatch.setenv("CASCADE_DB_PATH", str(tmp_path / "cascade.db"))
    import agent.tools.canvas as canvas
    import agent.config as config

    # signature default is None (not the literal "google")
    import inspect

    sig = inspect.signature(canvas.execute_node)
    assert sig.parameters["image_gen_provider"].default is None

    # create an image node, then execute WITHOUT passing a provider →
    # must fall back to config.IMAGE_GEN_PROVIDER (domestic apimart).
    # Use the DEFAULT user — set_user_id leaks via ContextVar across tests in the
    # same process, and other canvas tests rely on the default user being intact.
    canvas.set_user_id("default")
    canvas.set_thread_id("t-b6")
    monkeypatch.setattr(config, "IMAGE_GEN_PROVIDER", "apimart")
    res = canvas.create_canvas_node("image", "shot", "一只猫")  # positional (type, title, description)
    node_id = res["id"]
    canvas.execute_node(node_id, "image", "一只猫")  # no provider arg → config fallback

    state = canvas.get_canvas_state()
    node = next(n for n in state["nodes"] if n["id"] == node_id)
    assert node["image_gen_provider"] == "apimart"
