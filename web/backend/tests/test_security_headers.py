def test_responses_carry_security_headers(client) -> None:
    wrong_login = {"role": "doctor", "email": "nobody@example.com", "password": "wrong"}
    for response in (client.get("/health"), client.post("/auth/login", json=wrong_login)):
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["Referrer-Policy"] == "no-referrer"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["Cache-Control"] == "no-store"
