from newscheck.search import is_excluded


def test_social_media_is_excluded():
    for url in ["https://www.linkedin.com/posts/abc", "https://m.youtube.com/watch?v=1", "https://x.com/user/status/1"]:
        assert is_excluded(url), url


def test_news_sites_are_not_excluded():
    for url in ["https://www.reuters.com/a", "https://www.thehindu.com/b", "https://notx.com/c"]:
        assert not is_excluded(url), url