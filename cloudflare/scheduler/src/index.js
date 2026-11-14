// Starts the update-data workflow on time: GitHub's own schedule in update.yml is often late or dropped and stays
// only as a backup. Alerting is not done here: update.yml reports to healthchecks.io, which notifies when no
// successful run arrives, whoever (this Worker or GitHub's schedule) was supposed to start it.
const REPO = 'lis186/TaiwanRailwaySeats';
const WORKFLOW = 'update.yml';

export default {
  async scheduled(controller, env) {
    const res = await fetch(`https://api.github.com/repos/${REPO}/actions/workflows/${WORKFLOW}/dispatches`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${env.GITHUB_TOKEN}`,
        Accept: 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
        'User-Agent': 'TaiwanRailwaySeats-scheduler',
      },
      body: JSON.stringify({ ref: 'main' }),
    });
    // A failure shows in the Worker's logs; the missing run is what healthchecks.io notices.
    if (!res.ok) throw new Error(`dispatch: HTTP ${res.status} ${await res.text()}`);
  },
};
