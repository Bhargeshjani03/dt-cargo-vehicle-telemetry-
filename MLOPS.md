# DT-CARGO CI/CD and CT on Kuberns

This repo uses GitHub Actions for continuous integration and scheduled model training. Kuberns builds and deploys the web app from the protected release branch.

## Delivery flow

1. Open a pull request. The `CI` workflow installs the Python dependencies, runs the current test suite, and builds the Docker image.
2. Require the `CI / checks` status before merging to the release branch in GitHub branch protection or a repository ruleset.
3. Connect the GitHub repository in Kuberns and select that same protected release branch. Kuberns watches the selected branch and builds/deploys updates after they land.
4. Configure the Kuberns health check to use `/_stcore/health`. The container also includes a health check for that Streamlit endpoint.

Use the repo's protected `main` branch as the release branch. If the repo does not have `main` yet, choose or create the release branch in GitHub, make CI required there, then select it in Kuberns. Do not connect a working branch directly to the production app.

## Private data in the web app

Create a private Kuberns Storage bucket. Upload processed files using their repository-relative paths, for example:

```text
app-data/data/processed/engineered_tracks.csv
app-data/data/processed/tour_level/retained_tours_quality_checked.csv
app-data/data/processed/tour_level_clustering/12h_kernelpca_k3_tour_clusters.csv
app-data/src/anomaly_detection/reports/full/validation_predictions_extended_six_feature.csv
```

Set these environment variables in the Kuberns app settings. Use a read-only credential for the web app:

| Variable | Value |
|---|---|
| `KUBERNS_BUCKET_ID` | The private bucket identifier |
| `KUBERNS_ACCESS_KEY_ID` | The app's read-only storage credential ID |
| `KUBERNS_SECRET` | The matching secret |
| `KUBERNS_DATA_PREFIX` | `app-data` for the example keys above |

For local development, `DT_CARGO_DATA_DIR` can point to a local folder that contains the processed data tree. Keep credentials in Kuberns settings or a local untracked `.env`; do not commit them.

## Anomaly model continuous training

The `Anomaly model continuous training` workflow runs weekly and can also be started manually from GitHub Actions. It downloads the training dataset from Kuberns, uses the repo's existing chronological split and cluster-specific Isolation Forest training code, checks that all three cluster summaries and artifacts were produced, then uploads an immutable candidate folder:

```text
models/anomaly/candidates/<timestamp>-<github-run-id>/
```

Each candidate includes three model files, `validation_summary.json`, and `candidate_manifest.json`. The manifest records the input data SHA-256, source commit, validation summaries, and artifact hashes. The workflow never promotes a candidate or overwrites an active model.

Configure GitHub Actions repository secrets:

| Secret | Purpose |
|---|---|
| `KUBERNS_BUCKET_ID` | Bucket containing training data and candidates |
| `KUBERNS_ACCESS_KEY_ID` | Credential with read and write access to the bucket |
| `KUBERNS_SECRET` | Matching storage secret |

Optional GitHub Actions variables:

| Variable | Default | Purpose |
|---|---|---|
| `KUBERNS_TRAINING_KEY` | `training/anomaly/modeling_dataset.csv` | Bucket key for the prepared modeling dataset |
| `KUBERNS_CANDIDATE_PREFIX` | `models/anomaly/candidates` | Destination prefix for candidate files |

The training dataset must be the prepared anomaly modeling table expected by `src/anomaly_detection/src/train.py`. Candidate scores are not probabilities, the 2% review rate is a policy choice, and no verified labels exist to support an accuracy gate. An analyst must review a candidate and its validation window before any separate promotion step is added.

## Tour-duration training status

The duration model is not included in continuous training yet. The current training template has no planned distance, payload, or operation category values, while the baseline distance field is observed after a tour. Enable duration CT only after pre-departure features are populated, the feature set is fixed, and a chronological validation process is agreed.

## Kuberns setup still needed

- Connect the GitHub repository and select the protected release branch.
- Set the app's private-bucket read-only environment variables.
- Upload the processed app data and the anomaly training CSV to the keys above.
- Add the three GitHub Actions secrets; set the optional variables only if using different bucket keys.
- Add the GitHub ruleset requiring `CI / checks` on the release branch.

Platform references: [Kuberns Git integrations](https://docs.kuberns.com/docs/git-integrations), [health checks](https://www.docs.kuberns.com/docs/guides/health-checks), [environment variables](https://docs.kuberns.com/docs/guides/environment-variables), [Storage Buckets API](https://docs.kuberns.com/docs/storage-buckets/api-reference), and [GitHub rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets).
