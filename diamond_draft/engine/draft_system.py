"""Snake draft engine for Diamond Draft.

Encapsulates the full draft lifecycle: pick sequencing, human pick validation,
CPU auto-selection, and the snake (reversing) order algorithm. The human team
is always at index 0 in the team list and draft slot 1 in round 1.
"""
from __future__ import annotations

from diamond_draft.engine.score_engine import ScoreEngine
from diamond_draft.models.player import Player
from diamond_draft.models.team import Team


class DraftSystem:
    """Orchestrate a snake draft across all teams.

    Snake order: odd-numbered rounds go 0 → N-1 (left to right); even-numbered
    rounds go N-1 → 0 (right to left). The human team always drafts at index 0
    (first pick in round 1, last pick in round 2, and so on).

    CPU teams auto-pick the highest-scoring available player that fills an open
    roster slot. When a required position is fully exhausted, the CPU falls back
    to the best overall available player and forces the pick.

    Args:
        teams: All teams in the league. Must include exactly one human team
            at index 0 followed by CPU teams.
        player_pool: The full list of draftable players.
    """

    def __init__(self, teams: list[Team], player_pool: list[Player]) -> None:
        self._teams          = teams
        self._available:     list[Player] = list(player_pool)
        self._pick_sequence: list[int]    = self._build_snake_order()
        self._current_pick:  int          = 0

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def current_team(self) -> Team:
        """Return the team whose turn it is to pick.

        Returns:
            The ``Team`` object at the current position in the pick sequence.
        """
        return self._teams[self._pick_sequence[self._current_pick]]

    @property
    def current_pick_number(self) -> int:
        """Return the 1-based overall pick number (e.g. pick 7 of 84).

        Returns:
            Integer in the range ``[1, total_picks]``.
        """
        return self._current_pick + 1

    @property
    def total_picks(self) -> int:
        """Return the total number of picks in the entire draft.

        Returns:
            ``len(teams) * Team.MAX_ROSTER_SIZE``.
        """
        return len(self._pick_sequence)

    @property
    def is_complete(self) -> bool:
        """Return ``True`` when every team's roster is fully filled.

        Returns:
            ``True`` after the final pick has been made.
        """
        return self._current_pick >= len(self._pick_sequence)

    # ------------------------------------------------------------------
    # Player pool queries
    # ------------------------------------------------------------------

    def available_players(self) -> list[Player]:
        """Return all undrafted players sorted by fantasy score descending.

        Returns:
            List of ``Player`` objects; highest-scoring player first.
        """
        return sorted(self._available, key=ScoreEngine.score, reverse=True)

    def available_for_position(self, position: str) -> list[Player]:
        """Return undrafted players eligible for *position*, sorted by score.

        Args:
            position: Position code to filter by (e.g. ``"SP"``, ``"OF"``).

        Returns:
            Filtered and sorted list of available players at that position.
        """
        return [p for p in self.available_players() if p.position == position]

    # ------------------------------------------------------------------
    # Draft actions
    # ------------------------------------------------------------------

    def make_pick(self, player: Player, *, force: bool = False) -> None:
        """Draft *player* to the current team and advance the pick cursor.

        Args:
            player: The player to draft. Must be in the available pool.
            force: When ``True``, bypasses the position-slot check. Used by
                ``advance_cpu_turns`` when a required position is exhausted in
                the pool and the CPU must take a player regardless of slot fit.

        Raises:
            RuntimeError: If the draft is already complete.
            ValueError: If *player* is no longer available or if *force* is
                ``False`` and the current team has no open slot for the
                player's position.
        """
        if self.is_complete:
            raise RuntimeError("Draft is already complete.")
        if player not in self._available:
            raise ValueError(f"{player.name} is no longer available.")
        team = self.current_team
        if not force and not team.needs_position(player.position):
            raise ValueError(
                f"{team.name} has no open slot for position {player.position}."
            )
        self._available.remove(player)
        team.add_player(player)
        self._current_pick += 1

    def cpu_pick(self) -> Player:
        """Select the best available player that fills an open slot for the current team.

        Iterates over all available players (highest score first) and returns
        the first one the current team can accept. Falls back to the overall
        best player if no position-matched player exists (rare edge case when
        a position pool is fully exhausted).

        Returns:
            The chosen ``Player`` object.

        Raises:
            RuntimeError: If the entire player pool is empty.
        """
        team = self.current_team
        for player in self.available_players():
            if team.needs_position(player.position):
                return player
        # Exhausted all position-matched options — take the best remaining player.
        available = self.available_players()
        if not available:
            raise RuntimeError(
                f"Draft pool is completely exhausted for {team.name}."
            )
        return available[0]

    def advance_cpu_turns(self) -> list[Player]:
        """Auto-advance all consecutive CPU turns after the human picks.

        Continues making CPU picks until it is either the human team's turn
        or the draft is complete. The ``force`` flag is set when the CPU's
        best available player does not fit any open slot, preventing an
        infinite loop when rare position pools are exhausted.

        Returns:
            The list of players drafted by CPU teams during this call, in
            pick order.
        """
        picked: list[Player] = []
        while not self.is_complete and not self.current_team.is_human:
            player = self.cpu_pick()
            team   = self.current_team
            # Force the pick if the chosen player doesn't match an open slot
            # — this handles the edge case where a position is fully exhausted.
            force  = not team.needs_position(player.position)
            self.make_pick(player, force=force)
            picked.append(player)
        return picked

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_snake_order(self) -> list[int]:
        """Build the complete pick sequence for a snake draft.

        Odd rounds (0-indexed) go left-to-right; even rounds go right-to-left.

        Example with 3 teams, 2 rounds::

            Round 1: [0, 1, 2]
            Round 2: [2, 1, 0]
            Result:  [0, 1, 2, 2, 1, 0]

        Returns:
            Flat list of team indices, one entry per pick.
        """
        n            = len(self._teams)
        total_rounds = Team.MAX_ROSTER_SIZE
        order: list[int] = []
        for round_num in range(total_rounds):
            indices = range(n) if round_num % 2 == 0 else range(n - 1, -1, -1)
            order.extend(indices)
        return order
