from typing import Any, Callable, Optional, Set


DEFAULT_APPROVAL_TOOLS = {"edit_file", "exec_command", "remember"}


class ApprovalPolicy:
    def __init__(
        self,
        approver: Optional[Callable[[str, Any], bool]] = None,
        required_tools: Optional[Set[str]] = None,
        bypass: bool = False,
    ):
        self.approver = approver
        self.required_tools = set(required_tools or DEFAULT_APPROVAL_TOOLS)
        self.bypass = bypass

    def requires_approval(self, tool_spec):
        return (
            not self.bypass
            and (tool_spec.requires_approval or tool_spec.name in self.required_tools)
        )

    def request_approval(self, tool_spec, args):
        if not self.requires_approval(tool_spec):
            return True
        if self.approver is None:
            return False
        return bool(self.approver(tool_spec.name, args))
