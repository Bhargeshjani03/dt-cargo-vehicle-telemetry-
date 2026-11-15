"""Shared handles for links into the app's registered pages."""


_PAGE_LINKS = {}


def register_page_links(groups):
    """Keep the registered Streamlit Page objects available to page content."""
    global _PAGE_LINKS
    _PAGE_LINKS = {
        page.title: page
        for group_pages in groups.values()
        for page in group_pages
    }


def get_page_link(title):
    """Return a registered page by its visible title, if it exists."""
    return _PAGE_LINKS.get(title)
