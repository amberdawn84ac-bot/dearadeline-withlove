import "@testing-library/jest-dom";

// jsdom does not implement scrollIntoView; AdelineChatPanel calls it on every
// message update. Stub it once so dashboard/chat tests do not crash.
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = function scrollIntoView() {};
}
