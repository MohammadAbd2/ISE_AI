from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any

@dataclass(slots=True)
class PluginDescriptor:
    name: str; category: str; description: str; enabled: bool=True; capabilities: list[str]=field(default_factory=list)
    def to_dict(self)->dict[str,Any]: return asdict(self)
class PluginRegistry:
    def __init__(self):
        self._plugins={}
        for p in [
            PluginDescriptor('filesystem','core','Read, write, list, and validate sandbox files.',True,['read_file','write_file','list_files']),
            PluginDescriptor('terminal','core','Run allowlisted commands inside sandbox workspaces.',True,['run_command','build','test']),
            PluginDescriptor('browser','computer-use','Use Playwright to inspect and validate running apps.',True,['goto','screenshot','expect_text']),
            PluginDescriptor('artifact-export','delivery','Create verified ZIP exports with manifests.',True,['zip','manifest','download']),
            PluginDescriptor('preview-runtime','runtime','Start local previews for generated apps.',True,['preview','logs','stop']),
            PluginDescriptor('git','integration','Inspect repository state and prepare commits.',False,['status','diff']),
            PluginDescriptor('docker','runtime','Build and run isolated containers when enabled.',False,['build','run']),
        ]: self._plugins[p.name]=p
    def list(self)->list[dict[str,Any]]: return [p.to_dict() for p in self._plugins.values()]
    def get(self,name:str)->dict[str,Any]|None: return self._plugins[name].to_dict() if name in self._plugins else None
    def set_enabled(self,name:str,enabled:bool)->dict[str,Any]:
        if name not in self._plugins: raise KeyError(name)
        self._plugins[name].enabled=enabled; return self._plugins[name].to_dict()
_registry=PluginRegistry()
def get_plugin_registry()->PluginRegistry: return _registry
