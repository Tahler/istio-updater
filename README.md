# Istio Updater

Includes a Kubernetes CronJob which runs nightly, updating Istio to the latest
daily release.

This CronJob should be installed in "istio-system":

```bash
kubectl -n istio-system apply -f cron-job.yaml
```

`prom_scrape.py` is copied as a starter for querying Prometheus during the
update and reporting any errors that occur during the update. Traffic is assumed
to be ongoing during the update.

