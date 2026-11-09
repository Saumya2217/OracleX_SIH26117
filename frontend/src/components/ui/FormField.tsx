import React from "react";

interface FormFieldProps {
  id: string;
  label: string;
  hint?: string;
  children: React.ReactElement<{ "aria-describedby"?: string }>;
}

export const FormField: React.FC<FormFieldProps> = ({ id, label, hint, children }) => {
  const hintId = `${id}-hint`;
  const describedBy = [children.props["aria-describedby"], hint ? hintId : undefined].filter(Boolean).join(" ");
  return <div className="form-field">
    <label htmlFor={id}>{label}</label>
    {hint ? React.cloneElement(children, { "aria-describedby": describedBy }) : children}
    {hint && <p id={hintId} className="field-hint">{hint}</p>}
  </div>;
};
