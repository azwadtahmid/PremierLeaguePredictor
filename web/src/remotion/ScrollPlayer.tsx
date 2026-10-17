// Wraps the Remotion <Player> for the page:
// - "loop" players (the hero) autoplay muted and loop;
// - "once" players start when scrolled into view and stop on the last frame,
//   with a replay button;
// - with prefers-reduced-motion, nothing autoplays and players show their
//   final frame, so all information is still visible.
import { Player, type PlayerRef } from "@remotion/player";
import { useEffect, useRef, useState } from "react";

type AnyProps = Record<string, unknown>;

export function usePrefersReducedMotion() {
  const query = "(prefers-reduced-motion: reduce)";
  const [reduced, setReduced] = useState(() => window.matchMedia(query).matches);
  useEffect(() => {
    const media = window.matchMedia(query);
    const update = () => setReduced(media.matches);
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
  return reduced;
}

export function ScrollPlayer<P extends object>({
  component,
  inputProps,
  durationInFrames,
  fps,
  width,
  height,
  mode,
  label,
}: {
  component: React.ComponentType<P>;
  inputProps: P;
  durationInFrames: number;
  fps: number;
  width: number;
  height: number;
  mode: "loop" | "once";
  label: string;
}) {
  const playerRef = useRef<PlayerRef>(null);
  const boxRef = useRef<HTMLDivElement>(null);
  const reduced = usePrefersReducedMotion();
  // A ref, not state: changing it must not rebuild the observer.
  const played = useRef(false);

  useEffect(() => {
    const player = playerRef.current;
    const box = boxRef.current;
    if (!player || !box) return;
    if (reduced) {
      player.pause();
      player.seekTo(mode === "loop" ? Math.min(80, durationInFrames - 1) : durationInFrames - 1);
      return;
    }
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (mode === "loop") {
          if (entry.isIntersecting) player.play();
          else player.pause();
        } else if (entry.isIntersecting && !played.current) {
          played.current = true;
          player.seekTo(0);
          player.play();
        }
      },
      { threshold: 0.35 },
    );
    observer.observe(box);
    return () => observer.disconnect();
  }, [reduced, mode, durationInFrames]);

  const replay = () => {
    playerRef.current?.seekTo(0);
    playerRef.current?.play();
  };

  return (
    <div ref={boxRef} className={`player player-${mode}`} role="img" aria-label={label}>
      <Player
        ref={playerRef}
        component={component as React.ComponentType<AnyProps>}
        inputProps={inputProps as unknown as AnyProps}
        durationInFrames={durationInFrames}
        fps={fps}
        compositionWidth={width}
        compositionHeight={height}
        loop={mode === "loop"}
        // Without this the Player rewinds to frame 0 when it finishes, and
        // a play-once chart would go blank.
        moveToBeginningWhenEnded={false}
        controls={false}
        clickToPlay={false}
        doubleClickToFullscreen={false}
        spaceKeyToPlayOrPause={false}
        acknowledgeRemotionLicense
        style={{ width: "100%", aspectRatio: `${width} / ${height}` }}
      />
      {mode === "once" && !reduced && (
        <button type="button" className="replay" onClick={replay} aria-label={`Replay: ${label}`}>
          ↻ Replay
        </button>
      )}
    </div>
  );
}
