import flask
from requests.exceptions import HTTPError

from canonicalwebteam.discourse_docs.exceptions import (
    PathNotFoundError,
    RedirectFoundError,
)
from canonicalwebteam.discourse_docs.parsers import (
    parse_topic,
    parse_index,
    resolve_path,
)


class DiscourseDocs(object):
    """
    A Flask extension object to create a Blueprint
    to serve documentation pages, pulling the documentation content
    from Discourse.

    :param api: A DiscourseAPI for retrieving Discourse topics
    :param index_topic_id: ID of a forum topic containing nav & URL map
    :param category_id: Only show docs from topics in this forum category
    :param url_prefix: URL prefix for hosting under (Default: /docs)
    :param document_template: Path to a template for docs pages
                              (Default: docs/document.html)
    """

    def __init__(
        self,
        api,
        index_topic_id,
        category_id,
        document_template="docs/document.html",
    ):
        self.blueprint = flask.Blueprint("discourse_docs", __name__)

        @self.blueprint.route("/")
        @self.blueprint.route("/<path:path>")
        def document_view(path=""):
            """
            A Flask view function to serve
            topics pulled from Discourse as documentation pages.
            """

            # Ensure path has a leading slash
            path = "/" + path.lstrip("/")

            index = parse_index(api.get_topic(index_topic_id))

            if path == "/":
                document = index
            else:
                try:
                    topic_id = resolve_path(path, index["url_map"])
                except RedirectFoundError as redirect:
                    return flask.redirect(redirect.target_url)
                except PathNotFoundError:
                    return flask.abort(404)

                if topic_id == index_topic_id:
                    return flask.redirect("/")

                try:
                    topic = api.get_topic(topic_id)
                except HTTPError as http_error:
                    return flask.abort(http_error.response.status_code)

                if category_id and topic["category_id"] != category_id:
                    return flask.abort(404)

                document = parse_topic(topic)

                if (
                    topic_id not in index["url_map"]
                    and document["topic_path"] != path
                ):
                    return flask.redirect(document["topic_path"])

            return flask.render_template(
                document_template,
                document=document,
                navigation=index["navigation"],
                forum_url=api.base_url,
            )

    def init_app(self, app, url_prefix="/docs"):
        """
        Attach the discourse docs blueprint to the application
        at the specified `url_prefix`
        """

        app.register_blueprint(self.blueprint, url_prefix=url_prefix)