"use client";

import { Card, CardProps } from "@mui/material";
import { motion } from "framer-motion";
import React from "react";
import { expressiveSpring } from "./ExpressiveButton";

const MotionCard = motion.create(Card);

export const ExpressiveCard = React.forwardRef<HTMLDivElement, CardProps>(
  (props, ref) => {
    return (
      <MotionCard
        ref={ref}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        whileHover={{ y: -4, scale: 1.01 }}
        transition={expressiveSpring}
        {...props}
      />
    );
  }
);
ExpressiveCard.displayName = "ExpressiveCard";
