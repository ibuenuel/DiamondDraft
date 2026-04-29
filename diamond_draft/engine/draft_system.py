from __future__ import annotations

from diamond_draft.engine.score_engine import ScoreEngine
from diamond_draft.models.player import Player
from diamond_draft.models.team import Team


class DraftSystem:
    """
    Manages a snake draft across all teams.

    Snake order: odd rounds go 0 → N-1, even rounds go N-1 → 0.
    The human team is always index 0.
    CPU teams auto-pick the highest-scoring available player that fills
    an open roster slot.
    """

    def __init__(self, teams: list[Team], player_pool: list[Player]) -> None:
        self._teams = teams
        self._available: list[Player] = list(player_pool)
        self._pick_sequence: list[int] = self._build_snake_order()
        self._current_pick: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def current_team(self) -> Team:
        return self._teams[self._pick_sequence[self._current_pick]]

    @property
    def current_pick_number(self) -> int:
        return self._current_pick + 1

    @property
    def total_picks(self) -> int:
        return len(self._pick_sequence)

    @property
    def is_complete(self) -> bool:
        return self._current_pick >= len(self._pick_sequence)

    def available_players(self) -> list[Player]:
        """All undrafted players, sorted by fantasy score descending."""
        return sorted(self._available, key=ScoreEngine.score, reverse=True)

    def available_for_position(self, position: str) -> list[Player]:
        return [p for p in self.available_players() if p.position == position]

    def make_pick(self, player: Player) -> None:
        """Draft a player to the current team and advance the pick clock."""
        if self.is_complete:
            raise RuntimeError("Draft is already complete.")
        if player not in self._available:
            raise ValueError(f"{player.name} is no longer available.")
        team = self.current_team
        if not team.needs_position(player.position):
            raise ValueError(
                f"{team.name} has no open slot for position {player.position}."
            )
        self._available.remove(player)
        team.add_player(player)
        self._current_pick += 1

    def cpu_pick(self) -> Player:
        """Pick the best available player that fills an open slot for the current team."""
        team = self.current_team
        for player in self.available_players():
            if team.needs_position(player.position):
                return player
        raise RuntimeError(
            f"No eligible player found for {team.name}. "
            f"Open slots: {team.open_slots()}"
        )

    def advance_cpu_turns(self) -> list[Player]:
        """
        Auto-advance all consecutive CPU turns after the human picks.
        Returns the list of players the CPU teams selected.
        """
        picked: list[Player] = []
        while not self.is_complete and not self.current_team.is_human:
            player = self.cpu_pick()
            self.make_pick(player)
            picked.append(player)
        return picked

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_snake_order(self) -> list[int]:
        """
        Build the full pick sequence for a snake draft.

        Example with 3 teams and 2 rounds each:
          Round 1: [0, 1, 2]
          Round 2: [2, 1, 0]
        """
        n = len(self._teams)
        total_rounds = Team.MAX_ROSTER_SIZE
        order: list[int] = []
        for round_num in range(total_rounds):
            indices = range(n) if round_num % 2 == 0 else range(n - 1, -1, -1)
            order.extend(indices)
        return order
