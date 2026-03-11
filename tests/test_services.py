"""Tests for application services using a mock RedditPort."""

from unittest.mock import AsyncMock

import pytest
from redd.domain.enums import Category, SortOrder, TimeFilter, UserCategory
from redd.domain.models import PostDetail, SearchResult, SubredditPost, UserItem

from reddit_mcp_server.application.post_service import PostService
from reddit_mcp_server.application.search_service import SearchService
from reddit_mcp_server.application.user_service import UserService

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def mock_reddit():
    """Return a mock RedditPort with async methods."""
    mock = AsyncMock()
    mock.search.return_value = [
        SearchResult(
            title="Test Post",
            url="https://reddit.com/r/test/1",
            subreddit="test",
            description="A test post",
        ),
    ]
    mock.search_subreddit.return_value = [
        SearchResult(
            title="Sub Post",
            url="https://reddit.com/r/python/1",
            subreddit="python",
            description="In a subreddit",
        ),
    ]
    mock.get_post.return_value = PostDetail(
        title="Post Detail",
        author="user1",
        body="body text",
        score=42,
        url="https://reddit.com/r/test/post/1",
        subreddit="test",
        created_utc=1700000000.0,
        num_comments=5,
        comments=[],
    )
    mock.get_subreddit_posts.return_value = [
        SubredditPost(
            title="Hot Post",
            author="user2",
            permalink="/r/test/comments/abc/hot_post/",
            score=100,
            num_comments=10,
            created_utc=1700000000.0,
            subreddit="test",
            url="https://reddit.com/r/test/hot",
        ),
    ]
    mock.get_user.return_value = [
        UserItem(
            kind="comment",
            subreddit="test",
            url="https://reddit.com/r/test/comment/1",
            created_utc=1700000000.0,
            title=None,
            body="A comment",
        ),
    ]
    mock.get_user_posts.return_value = [
        SubredditPost(
            title="User Post",
            author="spez",
            permalink="/r/test/comments/def/user_post/",
            score=50,
            num_comments=3,
            created_utc=1700000000.0,
            subreddit="test",
            url="https://reddit.com/r/test/user_post",
        ),
    ]
    return mock


# ── SearchService ─────────────────────────────────────────────────────────────


class TestSearchService:
    async def test_search_defaults(self, mock_reddit):
        svc = SearchService(mock_reddit)
        results = await svc.search("python")

        mock_reddit.search.assert_awaited_once_with(
            "python",
            limit=25,
            sort=SortOrder.RELEVANCE,
        )
        assert len(results) == 1
        assert results[0].title == "Test Post"

    async def test_search_with_sort(self, mock_reddit):
        svc = SearchService(mock_reddit)
        await svc.search("python", sort="top", limit=5)

        mock_reddit.search.assert_awaited_once_with(
            "python",
            limit=5,
            sort=SortOrder.TOP,
        )

    async def test_search_subreddit_defaults(self, mock_reddit):
        svc = SearchService(mock_reddit)
        results = await svc.search_subreddit("python", "web scraping")

        mock_reddit.search_subreddit.assert_awaited_once_with(
            "python",
            "web scraping",
            limit=25,
            sort=SortOrder.RELEVANCE,
        )
        assert len(results) == 1


# ── PostService ───────────────────────────────────────────────────────────────


class TestPostService:
    async def test_get_post(self, mock_reddit):
        svc = PostService(mock_reddit)
        detail = await svc.get_post("/r/test/comments/abc/post/")

        mock_reddit.get_post.assert_awaited_once_with("/r/test/comments/abc/post/")
        assert detail.title == "Post Detail"
        assert detail.score == 42

    async def test_get_subreddit_posts_defaults(self, mock_reddit):
        svc = PostService(mock_reddit)
        posts = await svc.get_subreddit_posts("test")

        mock_reddit.get_subreddit_posts.assert_awaited_once_with(
            "test",
            limit=25,
            category=Category.HOT,
            time_filter=TimeFilter.ALL,
        )
        assert len(posts) == 1

    async def test_get_subreddit_posts_custom(self, mock_reddit):
        svc = PostService(mock_reddit)
        await svc.get_subreddit_posts("test", category="top", time_filter="week", limit=10)

        mock_reddit.get_subreddit_posts.assert_awaited_once_with(
            "test",
            limit=10,
            category=Category.TOP,
            time_filter=TimeFilter.WEEK,
        )


# ── UserService ───────────────────────────────────────────────────────────────


class TestUserService:
    async def test_get_user(self, mock_reddit):
        svc = UserService(mock_reddit)
        items = await svc.get_user("spez", limit=5)

        mock_reddit.get_user.assert_awaited_once_with("spez", limit=5)
        assert len(items) == 1

    async def test_get_user_posts_defaults(self, mock_reddit):
        svc = UserService(mock_reddit)
        posts = await svc.get_user_posts("spez")

        mock_reddit.get_user_posts.assert_awaited_once_with(
            "spez",
            limit=25,
            category=UserCategory.NEW,
            time_filter=TimeFilter.ALL,
        )
        assert len(posts) == 1

    async def test_get_user_posts_custom(self, mock_reddit):
        svc = UserService(mock_reddit)
        await svc.get_user_posts("spez", category="top", time_filter="month", limit=10)

        mock_reddit.get_user_posts.assert_awaited_once_with(
            "spez",
            limit=10,
            category=UserCategory.TOP,
            time_filter=TimeFilter.MONTH,
        )
