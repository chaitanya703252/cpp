"""
Group Matcher - matches students to study groups based on subjects and preferences.
"""


class GroupMatcher:
    """Matches students to relevant study groups based on subject overlap and preferences."""

    @staticmethod
    def calculate_similarity(user_subjects, group_subject):
        """
        Calculate how relevant a study group is to a student based on their subjects.

        Args:
            user_subjects: list of subject strings the student studies
            group_subject: the study group's subject string

        Returns:
            Similarity score (float between 0.0 and 1.0)
        """
        if not user_subjects or not group_subject:
            return 0.0

        user_subjects_lower = [s.lower().strip() for s in user_subjects]
        group_subject_lower = group_subject.lower().strip()

        # Exact match
        if group_subject_lower in user_subjects_lower:
            return 1.0

        # Partial match (subject contains or is contained)
        for subj in user_subjects_lower:
            if subj in group_subject_lower or group_subject_lower in subj:
                return 0.7

        # Related subjects mapping
        related = {
            "mathematics": ["statistics", "data_science", "physics", "engineering"],
            "physics": ["mathematics", "engineering", "chemistry"],
            "chemistry": ["biology", "physics", "medicine"],
            "biology": ["chemistry", "medicine", "psychology"],
            "computer_science": ["data_science", "mathematics", "engineering"],
            "data_science": ["statistics", "computer_science", "mathematics"],
            "statistics": ["mathematics", "data_science", "economics"],
            "economics": ["business", "statistics", "mathematics"],
            "business": ["economics", "law", "psychology"],
            "engineering": ["mathematics", "physics", "computer_science"],
            "psychology": ["biology", "medicine", "business"],
            "medicine": ["biology", "chemistry", "psychology"],
            "law": ["business", "economics", "history"],
            "history": ["law", "english", "economics"],
            "english": ["history", "psychology", "law"],
        }

        for subj in user_subjects_lower:
            related_subjects = related.get(subj, [])
            if group_subject_lower in related_subjects:
                return 0.4

        return 0.0

    @staticmethod
    def recommend_groups(user_subjects, all_groups, limit=5):
        """
        Recommend study groups for a student based on subject relevance.

        Args:
            user_subjects: list of subject strings
            all_groups: list of group dicts with 'subject' key
            limit: max number of recommendations

        Returns:
            List of (group, score) tuples sorted by relevance
        """
        scored = []
        for group in all_groups:
            score = GroupMatcher.calculate_similarity(user_subjects, group.get("subject", ""))
            if score > 0:
                scored.append((group, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]

    @staticmethod
    def find_groups_by_subject(subject, all_groups):
        """
        Find all groups that match a given subject exactly.

        Args:
            subject: subject string to search for
            all_groups: list of group dicts

        Returns:
            List of matching group dicts
        """
        if not subject:
            return []

        subject_lower = subject.lower().strip()
        return [
            g for g in all_groups
            if g.get("subject", "").lower().strip() == subject_lower
        ]

    @staticmethod
    def get_subject_popularity(all_groups):
        """
        Calculate how popular each subject is based on group count.

        Args:
            all_groups: list of group dicts

        Returns:
            Dict mapping subject to count, sorted by popularity
        """
        counts = {}
        for group in all_groups:
            subject = group.get("subject", "other").lower().strip()
            counts[subject] = counts.get(subject, 0) + 1

        return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))

    @staticmethod
    def check_group_availability(group, current_member_count):
        """
        Check if a group has available spots.

        Args:
            group: group dict with maxMembers
            current_member_count: current number of members

        Returns:
            Tuple of (is_available: bool, spots_remaining: int)
        """
        max_members = group.get("maxMembers", 12)
        try:
            max_members = int(max_members)
        except (ValueError, TypeError):
            max_members = 12

        spots = max_members - current_member_count
        return spots > 0, max(0, spots)
