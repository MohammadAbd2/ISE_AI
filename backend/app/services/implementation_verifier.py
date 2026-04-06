"""
Implementation verifier for validating new features before deployment.
Checks syntax, imports, and basic functionality.
"""

import ast
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.services.tool_executor import ToolExecutor


@dataclass
class ValidationResult:
    """Result of a validation check."""

    name: str
    passed: bool
    message: str
    details: Optional[dict] = None


class ImplementationVerifier:
    """
    Validates new code implementations before deployment.
    Performs syntax checks, import validation, and basic testing.
    """

    def __init__(self, tool_executor: Optional[ToolExecutor] = None):
        self.tool_executor = tool_executor or ToolExecutor()
        self.results: list[ValidationResult] = []

    def verify_implementation(
        self, file_path: str, run_tests: bool = False
    ) -> dict:
        """
        Perform comprehensive validation on a new implementation.
        
        Args:
            file_path: Path to the file to verify
            run_tests: If True, attempt to run tests
        
        Returns:
            dict with overall status and detailed results
        """
        self.results = []

        # 1. Check file exists
        if not self._check_file_exists(file_path):
            return self._build_report(False)

        # 2. Check syntax
        self._check_python_syntax(file_path)

        # 3. Check imports
        self._check_imports(file_path)

        # 4. Check PEP 8 compliance (basic)
        self._check_code_style(file_path)

        # 5. Run tests if requested
        if run_tests:
            self._run_tests(file_path)

        return self._build_report(all(r.passed for r in self.results))

    def _check_file_exists(self, file_path: str) -> bool:
        """Verify file exists and is readable."""
        try:
            path = Path(file_path)
            if not path.exists():
                self.results.append(
                    ValidationResult(
                        name="file_exists",
                        passed=False,
                        message=f"File not found: {file_path}",
                    )
                )
                return False

            if not path.is_file():
                self.results.append(
                    ValidationResult(
                        name="file_exists",
                        passed=False,
                        message=f"Not a file: {file_path}",
                    )
                )
                return False

            self.results.append(
                ValidationResult(
                    name="file_exists",
                    passed=True,
                    message=f"File found: {file_path}",
                )
            )
            return True
        except Exception as e:
            self.results.append(
                ValidationResult(
                    name="file_exists",
                    passed=False,
                    message=str(e),
                )
            )
            return False

    def _check_python_syntax(self, file_path: str) -> None:
        """Check Python syntax by parsing with AST."""
        try:
            content = self.tool_executor.read_file(file_path)
            ast.parse(content)
            self.results.append(
                ValidationResult(
                    name="python_syntax",
                    passed=True,
                    message="Python syntax is valid",
                )
            )
        except SyntaxError as e:
            self.results.append(
                ValidationResult(
                    name="python_syntax",
                    passed=False,
                    message=f"Syntax error: {e}",
                    details={"line": e.lineno, "offset": e.offset},
                )
            )
        except Exception as e:
            self.results.append(
                ValidationResult(
                    name="python_syntax",
                    passed=False,
                    message=f"Failed to parse: {e}",
                )
            )

    def _check_imports(self, file_path: str) -> None:
        """Check that all imports can be resolved."""
        try:
            content = self.tool_executor.read_file(file_path)
            tree = ast.parse(content)

            missing_imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if not self._can_import(alias.name):
                            missing_imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module and not self._can_import(node.module):
                        missing_imports.append(node.module)

            if missing_imports:
                self.results.append(
                    ValidationResult(
                        name="imports",
                        passed=False,
                        message=f"Missing imports: {', '.join(set(missing_imports))}",
                        details={"missing": list(set(missing_imports))},
                    )
                )
            else:
                self.results.append(
                    ValidationResult(
                        name="imports",
                        passed=True,
                        message="All imports are available",
                    )
                )
        except Exception as e:
            self.results.append(
                ValidationResult(
                    name="imports",
                    passed=False,
                    message=f"Failed to check imports: {e}",
                )
            )

    def _can_import(self, module_name: str) -> bool:
        """Check if a module can be imported."""
        try:
            __import__(module_name)
            return True
        except ImportError:
            return False

    def _check_code_style(self, file_path: str) -> None:
        """Check basic code style issues (simplified)."""
        try:
            content = self.tool_executor.read_file(file_path)
            lines = content.split("\n")

            issues = []
            for i, line in enumerate(lines, 1):
                # Check for trailing whitespace
                if line and line != line.rstrip():
                    issues.append(f"Line {i}: Trailing whitespace")

                # Check for tabs (PEP 8 recommends spaces)
                if "\t" in line:
                    issues.append(f"Line {i}: Use spaces instead of tabs")

            if issues:
                self.results.append(
                    ValidationResult(
                        name="code_style",
                        passed=False,
                        message=f"Found {len(issues)} style issues",
                        details={"issues": issues[:10]},  # Limit to first 10
                    )
                )
            else:
                self.results.append(
                    ValidationResult(
                        name="code_style",
                        passed=True,
                        message="Code style looks good",
                    )
                )
        except Exception as e:
            self.results.append(
                ValidationResult(
                    name="code_style",
                    passed=False,
                    message=f"Failed to check style: {e}",
                )
            )

    def _run_tests(self, file_path: str) -> None:
        """Attempt to run tests for the file."""
        try:
            # Look for test file
            base_path = Path(file_path)
            test_path = base_path.parent / f"test_{base_path.name}"

            if test_path.exists():
                result = self.tool_executor.execute_command(
                    f"python -m pytest {test_path} -v",
                    timeout=30,
                )
                if result["returncode"] == 0:
                    self.results.append(
                        ValidationResult(
                            name="tests",
                            passed=True,
                            message="Tests passed",
                        )
                    )
                else:
                    self.results.append(
                        ValidationResult(
                            name="tests",
                            passed=False,
                            message="Tests failed",
                            details={"stderr": result["stderr"][:500]},
                        )
                    )
            else:
                self.results.append(
                    ValidationResult(
                        name="tests",
                        passed=True,
                        message="No tests found (skipped)",
                    )
                )
        except Exception as e:
            self.results.append(
                ValidationResult(
                    name="tests",
                    passed=False,
                    message=f"Failed to run tests: {e}",
                )
            )

    def _build_report(self, overall_passed: bool) -> dict:
        """Build validation report."""
        return {
            "status": "success" if overall_passed else "failed",
            "overall_passed": overall_passed,
            "results": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "message": r.message,
                    "details": r.details,
                }
                for r in self.results
            ],
            "passed_count": sum(1 for r in self.results if r.passed),
            "failed_count": sum(1 for r in self.results if not r.passed),
        }

    def quick_validate(self, file_path: str) -> bool:
        """Quick validation: just syntax and imports."""
        self.results = []
        self._check_file_exists(file_path)
        self._check_python_syntax(file_path)
        self._check_imports(file_path)
        return all(r.passed for r in self.results)


def get_implementation_verifier(
    tool_executor: Optional[ToolExecutor] = None,
) -> ImplementationVerifier:
    """Dependency for FastAPI endpoints."""
    return ImplementationVerifier(tool_executor)
