"""Docker Sandbox Backend for deepagents.

Provides true OS-level container isolation for code and command execution,
implementing deepagents.backends.sandbox.BaseSandbox.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Optional

from deepagents.backends.protocol import (
    ExecuteResponse,
    FileDownloadResponse,
    FileUploadResponse,
)
from deepagents.backends.sandbox import (
    BaseSandbox,
)

logger = logging.getLogger(__name__)

DEFAULT_IMAGE = "data-analysis-sandbox:latest"
DEFAULT_TIMEOUT = 120


class DockerSandboxBackend(BaseSandbox):
    """Docker-based sandbox implementing SandboxBackendProtocol via BaseSandbox.

    Each backend instance manages an isolated Docker container with:
    - Dedicated filesystem volume / workspace mount
    - Dedicated memory and CPU constraints
    - Isolated process namespace
    - No access to host secrets, environment variables, or host filesystem
    """

    enable_capture_offload = False

    def __init__(
        self,
        image: str = DEFAULT_IMAGE,
        workspace_dir: str | Path | None = None,
        container_name: str | None = None,
        timeout: int = DEFAULT_TIMEOUT,
        mem_limit: str = "512m",
        cpus: float = 1.0,
        network: str = "none",
    ) -> None:
        """Initialize Docker sandbox container.

        Args:
            image: Docker image to use (defaults to data-analysis-sandbox:latest).
            workspace_dir: Host directory to mount into /workspace. If None, creates a temporary workspace.
            container_name: Optional custom container name.
            timeout: Default command execution timeout in seconds.
            mem_limit: Maximum memory limit for container (e.g. '512m', '1g').
            cpus: Maximum CPU cores allocated.
            network: Docker network mode ('none' for strict isolation).
        """
        self._image = image
        self._default_timeout = timeout
        self._mem_limit = mem_limit
        self._cpus = cpus
        self._network = network
        self._sandbox_id = f"docker-{uuid.uuid4().hex[:8]}"
        self._container_name = container_name or f"sandbox_{self._sandbox_id}"

        # Setup isolated workspace on host
        if workspace_dir is None:
            base_dir = Path(__file__).parent / "sandbox_workspaces" / self._sandbox_id
            self._workspace_dir = Path(base_dir).resolve()
        else:
            self._workspace_dir = Path(workspace_dir).resolve()

        self._workspace_dir.mkdir(parents=True, exist_ok=True)
        self._start_container()

    @property
    def id(self) -> str:
        """Return the unique sandbox identifier."""
        return self._sandbox_id

    @property
    def container_name(self) -> str:
        return self._container_name

    @property
    def workspace_dir(self) -> Path:
        return self._workspace_dir

    def _is_docker_available(self) -> bool:
        try:
            res = subprocess.run(
                ["docker", "info"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5,
                check=False,
            )
            return res.returncode == 0
        except Exception:
            return False

    def _start_container(self) -> None:
        """Launch the persistent Docker container for this sandbox session."""
        if not self._is_docker_available():
            raise RuntimeError(
                "Docker daemon is not running or unreachable. Please start Docker Desktop to use DockerSandboxBackend."
            )

        # Stop and remove any pre-existing container with this name
        subprocess.run(
            ["docker", "rm", "-f", self._container_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )

        cmd = [
            "docker", "run", "-d",
            "--name", self._container_name,
            "--memory", self._mem_limit,
            f"--cpus={self._cpus}",
            "--network", self._network,
            "-v", f"{self._workspace_dir}:/workspace",
            "-w", "/workspace",
            self._image,
            "tail", "-f", "/dev/null",
        ]

        logger.info("Starting Docker sandbox container: %s", self._container_name)
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
            check=False,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Failed to start Docker sandbox container: {result.stderr.strip()}")

    def execute(self, command: str, *, timeout: int | None = None) -> ExecuteResponse:
        """Execute a shell command inside the Docker container.

        Args:
            command: Shell command to run inside container.
            timeout: Command timeout in seconds.

        Returns:
            ExecuteResponse with output and exit code.
        """
        effective_timeout = timeout if timeout is not None else self._default_timeout
        cmd = [
            "docker", "exec",
            "-w", "/workspace",
            self._container_name,
            "/bin/sh", "-c", command,
        ]

        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=effective_timeout,
                check=False,
            )
            output = result.stdout or ""
            if result.stderr:
                output = f"{output}\n{result.stderr}" if output else result.stderr
            return ExecuteResponse(output=output, exit_code=result.returncode, truncated=False)

        except subprocess.TimeoutExpired:
            return ExecuteResponse(
                output=f"Command execution timed out after {effective_timeout} seconds.",
                exit_code=124,
                truncated=False,
            )
        except Exception as e:
            return ExecuteResponse(
                output=f"Error executing command in Docker sandbox: {str(e)}",
                exit_code=1,
                truncated=False,
            )

    def _resolve_host_path(self, container_path: str) -> Path:
        """Map a container path (/workspace/foo or /foo) to the host workspace dir."""
        norm_path = container_path.strip()
        if norm_path.startswith("/workspace/"):
            rel_path = norm_path[len("/workspace/"):]
        elif norm_path.startswith("/"):
            rel_path = norm_path.lstrip("/")
        else:
            rel_path = norm_path
        
        # Guard against traversal outside workspace
        target = (self._workspace_dir / rel_path).resolve()
        if not str(target).startswith(str(self._workspace_dir)):
            raise ValueError(f"Access denied: path '{container_path}' escapes sandbox workspace.")
        return target

    def upload_files(self, files: list[tuple[str, bytes]]) -> list[FileUploadResponse]:
        """Upload multiple files to the Docker sandbox workspace."""
        responses: list[FileUploadResponse] = []
        for path, content in files:
            try:
                host_target = self._resolve_host_path(path)
                host_target.parent.mkdir(parents=True, exist_ok=True)
                with open(host_target, "wb") as f:
                    f.write(content)
                
                # Also ensure root symlink if placed in root for compatibility
                if path.startswith("/") and not path.startswith("/workspace/"):
                    base_name = os.path.basename(path)
                    # Symlink inside container: /<filename> -> /workspace/<filename>
                    self.execute(f"ln -sf /workspace/{base_name} /{base_name}")

                responses.append(FileUploadResponse(path=path, error=None))
            except Exception as e:
                logger.error("Failed to upload file %s: %s", path, e)
                responses.append(FileUploadResponse(path=path, error=str(e)))
        return responses

    def download_files(self, paths: list[str]) -> list[FileDownloadResponse]:
        """Download multiple files from the Docker sandbox workspace."""
        responses: list[FileDownloadResponse] = []
        for path in paths:
            try:
                host_target = self._resolve_host_path(path)
                if not host_target.exists():
                    responses.append(FileDownloadResponse(path=path, content=None, error="file_not_found"))
                    continue
                if host_target.is_dir():
                    responses.append(FileDownloadResponse(path=path, content=None, error="is_directory"))
                    continue
                with open(host_target, "rb") as f:
                    content = f.read()
                responses.append(FileDownloadResponse(path=path, content=content, error=None))
            except Exception as e:
                logger.error("Failed to download file %s: %s", path, e)
                responses.append(FileDownloadResponse(path=path, content=None, error=str(e)))
        return responses

    def close(self) -> None:
        """Stop and remove the Docker container."""
        logger.info("Stopping Docker sandbox container: %s", self._container_name)
        subprocess.run(
            ["docker", "rm", "-f", self._container_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass
