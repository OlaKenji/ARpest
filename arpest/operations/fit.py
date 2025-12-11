"""Curve fitting helpers and fit-function registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

import numpy as np
from numpy.typing import ArrayLike
from scipy.optimize import curve_fit

from ..models import Dataset

@dataclass(frozen=True)
class FitParameterSpec:
    """Static metadata for an individual fit parameter."""

    name: str
    label: str
    default: float
    lower: float | None = None
    upper: float | None = None
    description: str | None = None


@dataclass(frozen=True)
class FitFunctionSpec:
    """Describes a reusable fit component (e.g., line, Lorentzian)."""

    id: str
    label: str
    description: str
    parameters: tuple[FitParameterSpec, ...]
    evaluator: Callable[[np.ndarray, dict[str, float]], np.ndarray]

    def evaluate(self, x: np.ndarray, params: dict[str, float]) -> np.ndarray:
        return self.evaluator(np.asarray(x, dtype=float), params)


@dataclass
class FitParameterConfig:
    """Runtime configuration for a parameter (value/fixing/bounds)."""

    name: str
    value: float
    fixed: bool = False
    lower: float | None = None
    upper: float | None = None


@dataclass
class FitComponentConfig:
    """User-configured component participating in a fit."""

    function_id: str
    parameters: dict[str, FitParameterConfig]
    label: str | None = None
    component_id: str | None = None


@dataclass
class FitComponentResult:
    """Result for an individual component after fitting."""

    label: str
    function_id: str
    parameters: dict[str, float]
    contribution: np.ndarray
    component_id: str | None = None
    metadata: dict[str, dict[str, float | bool | None]] | None = None


@dataclass
class FitResult:
    """Aggregated results for a curve-fit run."""

    success: bool
    message: str | None
    x: np.ndarray
    y_data: np.ndarray
    y_fit: np.ndarray
    components: list[FitComponentResult]
    residuals: np.ndarray
    r_squared: float | None
    covariance: np.ndarray | None


def fit_dataset(dataset: Dataset) -> Dataset:
    """Placeholder dataset-level fitting for compatibility."""

    return dataset.copy()


def available_fit_functions() -> list[FitFunctionSpec]:
    """Return all built-in fit functions (currently linear + Lorentzian)."""

    return list(_FIT_FUNCTIONS.values())


def get_fit_function(function_id: str) -> FitFunctionSpec:
    """Look up a fit function specification by identifier."""

    if function_id not in _FIT_FUNCTIONS:
        raise KeyError(f"Unknown fit function: {function_id}")
    return _FIT_FUNCTIONS[function_id]


def perform_curve_fit(
    x: ArrayLike,
    y: ArrayLike,
    components: Sequence[FitComponentConfig],
    *,
    fit_range: tuple[float, float] | None = None,
    max_evaluations: int = 4000,
) -> FitResult:
    """Execute a multi-component fit on 1D data."""

    if not components:
        raise ValueError("At least one fit component is required.")

    x_vals = np.asarray(x, dtype=float).ravel()
    y_vals = np.asarray(y, dtype=float).ravel()
    if x_vals.size == 0 or y_vals.size == 0 or x_vals.size != y_vals.size:
        raise ValueError("x/y arrays must be non-empty and share the same length.")

    mask = np.isfinite(x_vals) & np.isfinite(y_vals)
    if fit_range is not None:
        low, high = sorted(fit_range)
        mask &= (x_vals >= low) & (x_vals <= high)
    x_fit = x_vals[mask]
    y_fit = y_vals[mask]
    if x_fit.size < 2:
        raise ValueError("Not enough points in the selected fitting region.")

    resolved_components = []
    for comp in components:
        spec = get_fit_function(comp.function_id)
        params: dict[str, FitParameterConfig] = {}
        for spec_param in spec.parameters:
            override = comp.parameters.get(spec_param.name)
            if override is None:
                override = FitParameterConfig(
                    name=spec_param.name,
                    value=spec_param.default,
                    fixed=False,
                    lower=spec_param.lower,
                    upper=spec_param.upper,
                )
            else:
                if override.lower is None:
                    override.lower = spec_param.lower
                if override.upper is None:
                    override.upper = spec_param.upper
            params[spec_param.name] = override
        label = comp.label or spec.label
        resolved_components.append((spec, label, params, comp.component_id))

    variable_initial: list[float] = []
    lower_bounds: list[float] = []
    upper_bounds: list[float] = []

    for comp_index, (_, _, params, _) in enumerate(resolved_components):
        for pname, config in params.items():
            if config.fixed:
                continue
            variable_initial.append(config.value)
            lower_bounds.append(-np.inf if config.lower is None else config.lower)
            upper_bounds.append(np.inf if config.upper is None else config.upper)

    def _composite(x_input: np.ndarray, *theta: float) -> np.ndarray:
        theta_idx = 0
        total = np.zeros_like(x_input, dtype=float)
        for comp_idx, (spec, _, params, _) in enumerate(resolved_components):
            values: dict[str, float] = {}
            for pname, config in params.items():
                if config.fixed:
                    values[pname] = config.value
                else:
                    values[pname] = theta[theta_idx]
                    theta_idx += 1
            total += spec.evaluate(x_input, values)
        return total

    success = True
    message = None
    covariance = None
    param_errors: list[float | None] | None = None
    optimized = np.array(variable_initial, dtype=float)
    if variable_initial:
        bounds = (np.array(lower_bounds, dtype=float), np.array(upper_bounds, dtype=float))
        try:
            optimized, covariance = curve_fit(
                _composite,
                x_fit,
                y_fit,
                p0=variable_initial,
                bounds=bounds,
                maxfev=max_evaluations,
            )
            if covariance is not None:
                diag = np.diag(covariance)
                param_errors = []
                for value in diag:
                    if not np.isfinite(value) or value < 0:
                        param_errors.append(None)
                    else:
                        param_errors.append(float(np.sqrt(value)))
        except Exception as exc:  # pragma: no cover - SciPy errors are runtime specific
            success = False
            message = str(exc)
            covariance = None

    theta_idx = 0
    for comp_idx, (_, _, params, _) in enumerate(resolved_components):
        for pname, config in params.items():
            if config.fixed:
                continue
            config.value = float(optimized[theta_idx])
            theta_idx += 1

    y_fit_full = _composite(x_vals, *optimized)
    y_fit_subset = _composite(x_fit, *optimized)
    residuals = y_fit_subset - y_fit
    ss_tot = np.sum((y_fit - np.mean(y_fit)) ** 2)
    ss_res = np.sum(residuals**2)
    r_squared = None if ss_tot == 0 else 1 - ss_res / ss_tot

    components_result: list[FitComponentResult] = []
    error_idx = 0
    for spec, label, params, component_id in resolved_components:
        param_values = {name: cfg.value for name, cfg in params.items()}
        contribution = spec.evaluate(x_vals, param_values)
        metadata: dict[str, dict[str, float | bool | None]] = {}
        for name, cfg in params.items():
            error = None
            if not cfg.fixed:
                if param_errors is not None and error_idx < len(param_errors):
                    error = param_errors[error_idx]
                error_idx += 1
            metadata[name] = {
                "value": cfg.value,
                "fixed": cfg.fixed,
                "lower": cfg.lower,
                "upper": cfg.upper,
                "error": error,
            }
        components_result.append(
            FitComponentResult(
                label=label,
                function_id=spec.id,
                parameters=param_values,
                contribution=contribution,
                component_id=component_id,
                metadata=metadata,
            )
        )

    return FitResult(
        success=success,
        message=message,
        x=x_vals,
        y_data=y_vals,
        y_fit=y_fit_full,
        components=components_result,
        residuals=residuals,
        r_squared=r_squared,
        covariance=covariance,
    )


# ----------------------------------------------------------------------
# Built-in functions
# ----------------------------------------------------------------------


def _linear(x: np.ndarray, params: dict[str, float]) -> np.ndarray:
    slope = params.get("slope", 0.0)
    intercept = params.get("intercept", 0.0)
    return slope * x + intercept


def _lorentzian(x: np.ndarray, params: dict[str, float]) -> np.ndarray:
    amplitude = params.get("amplitude", 1.0)
    center = params.get("center", 0.0)
    gamma = max(params.get("gamma", 1.0), 1e-9)
    return amplitude * (gamma**2) / ((x - center) ** 2 + gamma**2)


_FIT_FUNCTIONS: dict[str, FitFunctionSpec] = {
    "linear": FitFunctionSpec(
        id="linear",
        label="Linear baseline",
        description="a*x + b",
        parameters=(
            FitParameterSpec("slope", "Slope", default=0.0),
            FitParameterSpec("intercept", "Intercept", default=0.0),
        ),
        evaluator=_linear,
    ),
    "lorentzian": FitFunctionSpec(
        id="lorentzian",
        label="Lorentzian peak",
        description="amp * gamma^2 / ((x - center)^2 + gamma^2)",
        parameters=(
            FitParameterSpec("amplitude", "Amplitude", default=1.0),
            FitParameterSpec("center", "Center", default=0.0),
            FitParameterSpec("gamma", "Gamma", default=0.1, lower=1e-6),
        ),
        evaluator=_lorentzian,
    ),
}
