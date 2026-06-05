from typing import Dict, List, Set, Tuple


class RouteBlocker:
    def __init__(self):
        self._blocked: Set[Tuple[str, str]] = set()

    def block(self, origen: str, destino: str) -> None:
        self._blocked.add((origen, destino))

    def unblock(self, origen: str, destino: str) -> None:
        self._blocked.discard((origen, destino))

    def is_blocked(self, origen: str, destino: str) -> bool:
        return (origen, destino) in self._blocked

    def get_blocked(self) -> List[Dict[str, str]]:
        return [
            {"origen": o, "destino": d}
            for o, d in sorted(self._blocked)
        ]

    def filter_edges(self, aristas: list) -> list:
        return [
            e for e in aristas
            if not self.is_blocked(e.origen, e.destino)
        ]

    def unblock_all(self) -> None:
        self._blocked.clear()
