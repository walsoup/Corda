"use client";

import { Button, ButtonProps } from "@mui/material";
import { motion } from "framer-motion";
import React from "react";

// M3 Expressive Spring Physics
// Lower damping and higher stiffness for a bouncy, organic feel.
export const expressiveSpring = {
  type: "spring",
  stiffness: 400,
  damping: 15,
  mass: 1,
};

const MotionButton = motion.create(Button);

export const ExpressiveButton = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (props, ref) => {
    return (
      <MotionButton
        ref={ref}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.92 }}
        transition={expressiveSpring}
        {...props}
      />
    );
  }
);
ExpressiveButton.displayName = "ExpressiveButton";
