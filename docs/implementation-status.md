# Implementation status

## Acceptance gates

- [ ] Pin and test Arena against the existing Isaac Sim 5.1 runtime without modifying it.
- [ ] Select direct reuse or documented adaptation based on a simulator smoke test.
- [ ] Integrate one mobile robot and one fixed 640×480 ego RGB camera.
- [ ] Validate physical move/turn/wait skills and private navigation evaluator.
- [ ] Connect gpt6.1-sol-light through a restricted model transport; prove input/tool isolation.
- [ ] Execute and record the first real task, including unsuccessful attempts.
- [ ] Run constraint-randomized pilot (proposed 64 episodes).
- [ ] Expand to stable batch generation (proposed 512), report diversity and cost.

External cameras and dense H5 export are later phases. Existing batch contracts stay unchanged.

## Development policy

Development and experimental commits belong on `dev`. Only verified components selected for retention are promoted to `main`. No experiment data, credentials, third-party assets or vendor checkouts belong in Git.

## Initial server inspection

Node43 is reachable. The existing runtime reports Isaac Sim `5.1.0-rc.19+release.26219.9c81211b.gl` in its VERSION file. Existing campaign manifests report 20/20 complete and 8/40 accepted; live simulator processes and the new campaign supervisor were confirmed. GPU memory usage alone is not a reservation signal.

All new simulation processes must acquire the same existing per-GPU lock:
`/local_nvme/zhangrong/isaac-rigidtrack-20261023/locks/campaign-gpu-{gpu}.lock`.

The new NAS workspace is `/mnt/nas/zhangrong/embodied-mosaic`, separate from existing campaigns. Arena source acquisition has started there. Its compatibility has not yet been tested.

## Prototype

`prototypes/episode_harness` contains the existing provider-independent protocol prototype. It has no model or simulator transport. See its README for the unimplemented runtime isolation and image validation requirements.
