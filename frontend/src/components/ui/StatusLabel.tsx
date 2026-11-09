import React from "react";

const labelFor = (value: string) => value.replaceAll("_", " ").toLowerCase().replace(/^./, (letter) => letter.toUpperCase());

export const StatusLabel: React.FC<{ value: string }> = ({ value }) => (
  <span className={`status-label status-label-${value.toLowerCase()}`}>{labelFor(value)}</span>
);
