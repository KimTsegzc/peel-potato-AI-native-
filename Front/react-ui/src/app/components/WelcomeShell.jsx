import { useLayoutEffect, useMemo, useRef, useState } from "react";

import { Composer } from "./Composer";
import { InteractiveAvatar } from "./InteractiveAvatar";

function splitWelcomeTitle(text, forceMultiline = false) {
  const value = String(text || "").trim();
  const characters = Array.from(value);
  if (!forceMultiline && characters.length <= 16) {
    return { multiline: false, lines: [value] };
  }

  const commaMatches = Array.from(value.matchAll(/[，,]/g));
  const commaIndex = commaMatches.length
    ? commaMatches[commaMatches.length - 1].index ?? -1
    : -1;
  if (commaIndex >= 0) {
    const firstLine = value.slice(0, commaIndex + 1).trim();
    const secondLine = value.slice(commaIndex + 1).trim();
    if (firstLine && secondLine) {
      return {
        multiline: true,
        lines: [firstLine, secondLine],
      };
    }
  }

  return {
    multiline: true,
    lines: [characters.slice(0, 10).join(""), characters.slice(10).join("")],
  };
}

export function WelcomeShell({ statusText, composerProps }) {
  const copyRef = useRef(null);
  const measureRef = useRef(null);
  const [titleLayout, setTitleLayout] = useState({
    text: "",
    forceMultiline: false,
    ready: false,
  });
  const titleText = String(statusText || "").trim();

  useLayoutEffect(() => {
    const copyElement = copyRef.current;
    const measureElement = measureRef.current;
    if (!copyElement || !measureElement) {
      return undefined;
    }

    if (!titleText) {
      setTitleLayout({ text: "", forceMultiline: false, ready: true });
      return undefined;
    }

    let frameId = 0;

    const evaluateOverflow = () => {
      const availableWidth = copyElement.clientWidth;
      if (!availableWidth) {
        frameId = window.requestAnimationFrame(evaluateOverflow);
        return;
      }

      const isOverflowing = measureElement.scrollWidth > availableWidth + 1;
      setTitleLayout((current) => {
        const hasSameText = current.text === titleText;
        const nextForceMultiline = hasSameText
          ? current.forceMultiline || isOverflowing
          : isOverflowing;

        if (
          hasSameText
          && current.forceMultiline === nextForceMultiline
          && current.ready
        ) {
          return current;
        }

        return {
          text: titleText,
          forceMultiline: nextForceMultiline,
          ready: true,
        };
      });
    };

    evaluateOverflow();
    const resizeObserver = typeof ResizeObserver === "function"
      ? new ResizeObserver(() => evaluateOverflow())
      : null;
    resizeObserver?.observe(copyElement);
    window.addEventListener("resize", evaluateOverflow);

    return () => {
      window.cancelAnimationFrame(frameId);
      resizeObserver?.disconnect();
      window.removeEventListener("resize", evaluateOverflow);
    };
  }, [titleText]);

  const isResolved = titleLayout.text === titleText && titleLayout.ready;
  const forceMultiline = titleLayout.text === titleText && titleLayout.forceMultiline;

  const title = useMemo(
    () => splitWelcomeTitle(titleText, forceMultiline),
    [titleText, forceMultiline],
  );

  return (
    <div className="welcome-stack-shell">
      <section className="hero-panel">
        <InteractiveAvatar className="hero-avatar" alt="鑫哥头像" />
        <div ref={copyRef} className={`hero-copy${title.multiline ? " is-multiline" : " is-singleline"}`}>
          <h1 ref={measureRef} aria-hidden="true" className="hero-title hero-title-measure">
            {titleText}
          </h1>
          <h1 className={`hero-title${title.multiline ? " is-multiline" : " is-singleline"}${isResolved ? " is-ready" : " is-pending"}`}>
            {title.lines.map((line, index) => (
              <span key={`${line}-${index}`} className="hero-title-line">
                {line}
              </span>
            ))}
          </h1>
        </div>
      </section>

      <Composer {...composerProps} />
    </div>
  );
}
