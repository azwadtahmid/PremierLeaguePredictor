// Premier League brand palette, shared by the page CSS and Remotion compositions.
import { loadFont as loadOutfit } from "@remotion/google-fonts/Outfit";
import { loadFont as loadBarlow } from "@remotion/google-fonts/BarlowCondensed";

export const PL = {
  purple: "#38003C",
  white: "#FFFFFF",
  green: "#00FF85",
  pink: "#E90052",
  cyan: "#04F5FF",
  // Shades of the same purple, for depth.
  purpleDeep: "#24002A",
  purpleSoft: "#4C1452",
} as const;

export const { fontFamily: bodyFont } = loadOutfit("normal", {
  weights: ["400", "500", "600", "700", "800"],
  subsets: ["latin"],
});

export const { fontFamily: displayFont } = loadBarlow("normal", {
  weights: ["600", "700", "800"],
  subsets: ["latin"],
});

// Race-chart lines, in a fixed order (never cycled). Only four teams get a
// colour; any others are drawn as faint context lines.
export const SERIES = [PL.green, PL.cyan, PL.pink, PL.white] as const;

// Home / draw / away colours used everywhere a probability is shown.
export const RESULT_COLOUR = { H: PL.green, D: PL.white, A: PL.cyan } as const;
