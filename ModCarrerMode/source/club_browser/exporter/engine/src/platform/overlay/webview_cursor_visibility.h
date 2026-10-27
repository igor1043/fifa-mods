#ifndef FIFA_WEBVIEW_CURSOR_VISIBILITY_H
#define FIFA_WEBVIEW_CURSOR_VISIBILITY_H

// ShowCursor is a counter, not a boolean. Undo precisely our own increments.
struct WebViewCursorVisibility {
    bool acquired = false;
    int increments = 0;
    template<class Show> void set_visible(bool visible, Show show) {
        if (visible == acquired) return;
        acquired = visible;
        if (visible) {
            int count;
            do { count = show(true); ++increments; }
            while (count < 0 && increments < 64);
        } else {
            while (increments > 0) { show(false); --increments; }
        }
    }
};
#endif
