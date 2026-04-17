import "./TarsSpinner.css";

export default function TarsSpinner({ size = "medium", tone = "signal" }) {
  return (
    <span className={`tars-spinner ${size} ${tone}`} aria-hidden="true">
      <span className="spinner-arm arm-one" />
      <span className="spinner-arm arm-two" />
      <span className="spinner-arm arm-three" />
      <span className="spinner-arm arm-four" />
    </span>
  );
}
