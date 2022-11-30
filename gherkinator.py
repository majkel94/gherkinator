import os
from dataclasses import dataclass

import click
import dotenv
from azure.devops.connection import Connection
from azure.devops.released.work_item_tracking import WorkItemTrackingClient, WorkItem
from msrest.authentication import BasicAuthentication

from bs4 import BeautifulSoup

dotenv.load_dotenv()

user = os.environ.get("GHERKINATOR_USER")
personal_access_token = os.environ.get("GHERKINATOR_TOKEN")
organization = os.environ.get("GHERKINATOR_ORG")
project = os.environ.get("GHERKINATOR_PROJECT")


@dataclass
class Step:
    keyword: str
    value: str

    def __str__(self):
        return f"{self.keyword} {self.value}"


@dataclass
class Scenario:
    feature: str
    steps: list[Step]

    def __str__(self):
        steps = "\n\t".join(map(str, self.steps))
        return f"Feature: {self.feature}\n\n\t{steps}"


def get_azure_client(org_name: str, user: str, pat: str) -> WorkItemTrackingClient :
    credentials = BasicAuthentication(username=user, password=pat)
    base_url = f"https://dev.azure.com/{org_name}"
    connection = Connection(base_url=base_url, creds=credentials)

    return connection.clients.get_work_item_tracking_client()


def parse_scenario(work_item: WorkItem) -> Scenario:
    wit_steps = work_item.fields["Microsoft.VSTS.TCM.Steps"]

    steps: list[Step] = []

    steps_soup = BeautifulSoup(wit_steps, "html.parser")
    for step_idx, step_tag in enumerate(steps_soup.find_all("step")):
        step_description = BeautifulSoup(step_tag.text, "html.parser").find_all("p")
        action, result = step_description

        step = Step(
            keyword=f"{'When' if step_idx == 0 else 'And'}",
            value=f"I {action.text}",
        )
        steps.append(step)
        step = Step(keyword="Then", value=result.text.replace('\n', ' '))
        steps.append(step)

    return Scenario(feature=work_item.fields["System.Title"], steps=steps)


@click.command()
@click.option("--task", help="Id of DevOps Azure Work Item")
def generate_gherkin(task) -> str:
    azure = get_azure_client(organization, user, personal_access_token)

    wit: WorkItem = azure.get_work_item(task, project=project)
    scenario: Scenario = parse_scenario(wit)

    click.echo(scenario)
    return str(scenario)


if __name__ == '__main__':
    generate_gherkin()


