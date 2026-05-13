"use client";

import { createTheme } from "@mui/material/styles";

export const m3Theme = createTheme({
  palette: {
    mode: "dark",
    primary: {
      main: "#d0bcff",
      contrastText: "#381e72",
    },
    secondary: {
      main: "#ccc2dc",
      contrastText: "#332d41",
    },
    background: {
      default: "#1c1b1f",
      paper: "#2b2930",
    },
    surfaceTint: "#d0bcff",
  },
  shape: {
    borderRadius: 24, // M3 Expressive favors highly rounded, organic shapes
  },
  typography: {
    fontFamily: "var(--font-geist-sans), Roboto, Helvetica, Arial, sans-serif",
    button: {
      textTransform: "none",
      fontWeight: 500,
      letterSpacing: "0.01em",
    },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 100, // fully rounded pills
          padding: "10px 24px",
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 28,
          backgroundImage: "none", // remove M2 elevation overlays
          boxShadow: "none",
          backgroundColor: "#2b2930",
        },
      },
    },
  },
});
