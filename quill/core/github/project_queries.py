"""Fixed GraphQL documents for the GitHub Projects workbench."""

_PROJECTS_QUERY = """
query($owner:String!, $repo:String!, $after:String) {
  repository(owner:$owner, name:$repo) {
    projectsV2(first:50, after:$after) {
      pageInfo { hasNextPage endCursor }
      nodes { id title number url shortDescription closed }
    }
  }
}
"""

_BOARD_QUERY = """
query($projectId:ID!, $after:String) {
  node(id:$projectId) {
    ... on ProjectV2 {
      id title number url
      fields(first:100) {
        pageInfo { hasNextPage }
        nodes {
          __typename id name
          ... on ProjectV2SingleSelectField { options { id name } }
          ... on ProjectV2MultiSelectField { multiSelectOptions { id name } }
          ... on ProjectV2IterationField {
            configuration { iterations { id title startDate duration } }
          }
        }
      }
      items(first:100, after:$after) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id type isArchived
          content {
            ... on Issue {
              id number title state url repository { nameWithOwner }
              blockedBy(first:20) {
                pageInfo { hasNextPage }
                nodes { id number title state url repository { nameWithOwner } }
              }
              blocking(first:20) {
                pageInfo { hasNextPage }
                nodes { id number title state url repository { nameWithOwner } }
              }
              subIssues(first:20) {
                pageInfo { hasNextPage }
                nodes { id number title state url repository { nameWithOwner } }
              }
              subIssuesSummary { total completed percentCompleted }
            }
            ... on PullRequest {
              id number title state url repository { nameWithOwner }
            }
            ... on DraftIssue { id title body }
          }
          fieldValues(first:50) {
            pageInfo { hasNextPage }
            nodes {
              __typename
              ... on ProjectV2ItemFieldTextValue { text field { id name } }
              ... on ProjectV2ItemFieldNumberValue { number field { id name } }
              ... on ProjectV2ItemFieldDateValue { date field { id name } }
              ... on ProjectV2ItemFieldSingleSelectValue {
                name optionId field { id name }
              }
              ... on ProjectV2ItemFieldMultiSelectValue {
                value options { id name } field { id name }
              }
              ... on ProjectV2ItemFieldIterationValue { title iterationId field { id name } }
            }
          }
        }
      }
    }
  }
}
"""

_ISSUE_QUERY = """
query($owner:String!, $repo:String!, $number:Int!) {
  repository(owner:$owner, name:$repo) {
    issue(number:$number) {
      id number title state url repository { nameWithOwner }
    }
  }
}
"""

__all__ = ["_BOARD_QUERY", "_ISSUE_QUERY", "_PROJECTS_QUERY"]
