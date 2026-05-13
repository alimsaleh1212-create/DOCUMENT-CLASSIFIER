import "@testing-library/jest-dom";

// Silence React Router v6→v7 future flag warnings in tests
const originalWarn = console.warn.bind(console);
console.warn = (...args: unknown[]) => {
  if (typeof args[0] === "string" && args[0].includes("React Router Future Flag Warning")) return;
  originalWarn(...args);
};
