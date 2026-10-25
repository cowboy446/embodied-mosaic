# Implementation status

## Acceptance gates

- [ ] Pin and test Arena against the existing Isaac Sim 5.1 runtime without modifying it.
- [ ] Select direct reuse or documented adaptation based on a simulator smoke test.
- [ ] Integrate one mobile robot and one fixed 640×480 ego RGB camera.
- [ ] Validate physical move/turn/wait skills and private navigation evaluator.
- [ ] Connect gpt-6.1-sol through a restricted model transport; prove input/tool isolation.
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

### Native ego diagnostic queued

A server-only `scripts/ego_smoke.py` diagnostic loads an accepted Carter scene in a new USD layer, disables the other robot actors, attaches a single RGB camera, and applies short native wheel commands. It is a sensor/control diagnostic, not an agent episode and not a task success result.

Server output: `/mnt/nas/zhangrong/embodied-mosaic/runs/ego-smoke-001`.
Latest queued lock process: PID 695642 on node43 (revalidate before acting). It uses the shared GPU 7 lock. The source was corrected before simulation launch to the explicit slot `source_episode`, rather than inferring provenance from the copied H5 path.

Arena release/0.1.1 pins Isaac Lab commit `6acdd82a1633732d32bb575e3d792e34fdeb437e`, whose VERSION reports 2.3.0. Arena's default Docker base is Sim 5.0.0; compatibility with our 5.1 remains to be tested. Source was transferred to the NAS vendor directory. Current server driver is 580.65.06; no Arena or Sim 6.2 container was found in the local Docker image inventory.

### Ego diagnostic 002 and dependency overlay

The second native smoke run completed 90 RGB frames (640×480). Frame 19 was visually inspected: warehouse shelving, floor and wall were visible with no robot self-occlusion in that sample. Measured forward displacement between frames 15 and 59 was 0.17374 m. The wrapped yaw change during the short turn was approximately 2.98 degrees, below the roughly 9-degree command; closed-loop skill endpoint control is still required. No agent task was executed.

The first smoke attempt failed with an empty RGB annotator buffer. Explicit Replicator capture fixed that failure. Logs for both attempts remain on NAS.

Seven missing Python dependencies were installed into a project-specific `runtime/python-deps` directory using offline wheels. The server's default package mirror timed out, so it was not used further. The existing simulation package environment was not modified. Arena probe 001 is queued/running under the shared GPU 7 lock, PID 721291; inspect its result before claiming compatibility.

The user confirmed the model setting as `gpt-6.1-sol` with `low` reasoning. The config and protocol tests now assert that setting; a live restricted model transport remains unverified.

### Feedback control and restricted CLI investigation

Feedback smoke 001 completed on node43: a 0.20 m forward request moved approximately 0.1931 m; a 20-degree turn changed yaw approximately 19.03 degrees. All three diagnostic skills reached their endpoint criteria. This is not yet a collision-tested navigation episode. Private diagnostics remain in `runs/ego-feedback-001/diagnostic.json` on NAS.

Arena probe 002 imported its environment, scene and asset registry successfully after adding hidapi to the isolated dependency overlay. Ground-plane spawning failed with a None collision-prim path passed to Stage.GetPrimAtPath. Runtime compatibility is still unverified; the ground asset resolution and spawn path need inspection.

The user confirmed that only Codex login is available and requested continued investigation of restricted CLI transport. Installed CLI version: 0.140.0. Its help exposes ignore-user-config, ignore-rules, ephemeral sessions, image input and output-schema. A bubblewrap user/PID namespace smoke test succeeded locally; it used a read-only root bind solely to check availability, NOT to prove filesystem isolation.

The generated app-server schema supports explicit base instructions, ephemeral sessions and environment selection. An empty dynamicTools list does not establish that built-in tools are absent. Current upstream source registers apply_patch based on model metadata independently of the shell-tool switch. Therefore disabling shell alone is insufficient. This source inspection uses upstream main, not a verified source match for the installed binary. No isolated model call has passed acceptance yet.

Next transport gates: a minimal filesystem allowlist; no inherited project/user instructions or plugins; explicit tool inventory verification; out-of-sandbox canary rejection; a live ego-image to skill-JSON call using gpt-6.1-sol at low reasoning. Authentication must stay outside model-visible context and all credential material stays out of Git and episode logs.

References inspected: https://github.com/openai/codex/blob/main/codex-rs/core/src/tools/spec_plan.rs and https://github.com/openai/codex/blob/main/codex-rs/core/config.schema.json.

### Offline CLI audit 009

An actual request emitted by installed CLI 0.140.0 was captured by a dummy localhost Responses provider. No live model was called; request headers and authentication were not logged. The first connection attempt was inadvertently routed through a host proxy; removing proxy variables for the localhost-only audit fixed it.

Changing model transport metadata to direct tool mode and disabled multi-agent mode removed code execution and collaboration tools. A bubblewrap allowlist mounted system runtime directories plus the temporary request directory, excluding host home, project directories and NAS. Disabling automatic skills and permission instruction blocks produced a request containing only the CLI environment context and the explicit audit prompt. This verifies the captured context boundary for this offline configuration, not the live authenticated transport.

Two tools remain registered: update_plan and view_image. Consequently strict no-tool acceptance remains open. Host authentication was deliberately not mounted during this test. Next: enforce an episode-only image surface, test outside-path rejection, and establish authenticated image/JSON transport without exposing credentials through tools.

### Observation validation and filesystem probe

The episode protocol now fully decodes PNG inputs, requires a single 640x480 RGB frame, and re-encodes only pixel data to strip nonvisual metadata. It rejects replacing an already issued observation. Eight boundary tests pass, including malformed images, dimensions/channels and metadata leakage checks. Pillow is now an explicit prototype dependency.

Offline CLI audit 010 executes path-visibility assertions inside the same bubblewrap namespace: host auth.json, the current project directory and /mnt/nas are absent. This verifies these specific filesystem exclusions; authenticated transport and complete tool removal remain unverified.

Arena diagnostic 003 was queued on node43 under the existing GPU 7 lock (PID 804957). It records the ground asset URI and loaded prim types on failure. Revalidate its process/output before interpreting the result.

### Body observations, skill profiles, and Arena asset diagnosis

The user expanded allowed observations to nonprivileged proprioception. The protocol now accepts optional encoder and body-frame IMU channels with exact field validation; global poses and arbitrary simulator dictionaries remain excluded. No sensor-source provenance claim is made until the corresponding simulator adapter is audited.

Skill definitions now live in an embodiment registry. The Carter base profile drives both public schema and action validation, with per-episode copies. Unknown/unimplemented profiles fail closed. Persistent VLA/motion-tracking lifecycle and actuator ownership requirements are documented but not implemented. Thirteen boundary tests pass.

Arena probe 003 never launched because the shell wrapper was not executable; probe 004 used bash explicitly. It revealed ground_usd_path = None/Isaac/Environments/Grid/default_environment.usd, with no loaded geometry. Isaac Lab reads /persistent/isaac/asset_root/cloud at import time; this setting was absent. Probe 005 explicitly supplies the 5.1 asset root found in the installed asset-browser configuration and is queued/running under the same GPU 7 lock (PID 828974). This is a configuration diagnosis, not proof of full Arena compatibility.

Probe 005 completed its scoped checks successfully: environment/scene/registry imports and ten Isaac Lab simulation steps. Saved evidence: evidence/arena-probe-005.json. Full Carter Scene × Robot × Task execution remains unverified.

### Authenticated CLI result and prompt-constrained pilot

Live CLI smoke 001 authenticated successfully but the backend rejected gpt-6.1-sol with model_not_found / not supported for this ChatGPT account transport. No model action was returned or executed. No fallback model was selected. The user explicitly authorized a fresh-context gpt-6.1-sol + low subagent for the first prompt-constrained closed loop while strict tool isolation remains open.

A mailbox-driven server pilot and coordinator-only SSH bridge were added. The policy sees RGB, semantic goal, skill bounds, own recent actions and wheel encoder readings. Target coordinates and poses are confined to the server's private logs/evaluation. The pilot uses a forward ray fan, not a full swept-volume collision certificate, and must not count toward batch safety acceptance. Queued on node43 with GPU 7 lock: ego-agent-001, PID 853804.

Arena probe 005 completed its reported checks but its process remained alive in shutdown for over five minutes, retaining the GPU lock. The exact diagnostic child PID 830227 was verified and sent SIGTERM; the incident is recorded on NAS. Thus successful stepping does not establish clean runtime lifecycle compatibility.

### First prompt-constrained episode completed

Episode ego-agent-001 ran on node43 GPU 7 and exited normally. A fresh-context gpt-6.1-sol low policy selected move_forward 0.3 m twice, then finish. The independent private evaluator measured 1.21455 m remaining from robot center to target and rejected task success. Both movement controllers returned reached; final settling speed was 0.000612 m/s. This is a completed closed-loop pilot with policy failure, not a successful navigation task or strict-isolation acceptance. 255 RGB frames including initial observation and a 30 fps MP4 are retained on NAS; the small preview and observation packets are copied locally under runs/policy-001. The policy agent has ended and must not be reused for another episode.

A scheduling attempt to move the waiting pilot to GPU 3 raced with the original GPU 7 start. Its precondition correctly detected an existing child, but the surrounding shell lacked fail-fast behavior and continued. The duplicate failed at exclusive output-directory creation before SimulationApp initialization. The original run remained active; its PID file was restored. Future scheduling scripts must fail closed on prerequisite checks.

Local harness.py was observed changed back to an older interface outside this edit sequence. Its contents were preserved under runs/external-edits and not overwritten. Server pilot used the previously uploaded proprioception/skill-registry version. Reconcile the local edit before deploying subsequent episodes.

### Calibrated observations and volume query tests

The user confirmed the local harness rollback was accidental; the committed proprioception/profile interface was restored. Public observations now include fixed camera intrinsics, mounting transform and drive dimensions from one robot_model definition also consumed by the renderer. The goal explicitly measures horizontal distance from the base center. No live target distance or world pose is supplied. Fourteen protocol tests pass.

Node43 collision probe 001 passed thin off-axis, self-filter/clear-path, rotation-side and overhead obstacle cases using the installed PhysX query API. The pilot now derives a conservative envelope from the rendered robot world bound and uses overlap/sweep queries. This new integration has not run yet; the flat-ground exclusion below 2.5 cm and unverified contact dynamics mean it is not full safety certification.

Existing batch manifest check: old 20 accepted; diverse40 has 9 accepted, 8 running, 22 pending and 1 rejected. This count is manifest-level evidence, not a fresh per-file revalidation.

### Full robot recorder and rule-grid baseline

Recorder probe 001 completed normally on node43: 85 RGB/state frames over 2.80000015 seconds, all four Carter joints, base pose/velocities, control targets and actual simulator clock. SHA-256 image and cadence audit passed. This was a scripted 0.1 m diagnostic, not an agent success. Original episode third-person kinematic replay is delivered locally; missing historical wheel states remain unavailable.

User stopped diverse40 and deferred embodied-agent integration in favor of rule-based grid navigation. Stopped the identified diverse40 scheduler/workers and render processes, retained 9 accepted episodes and all artifacts, saved process snapshot and manifest backup on NAS. Disabled the old batch heartbeat to prevent automatic restart. Old20 is untouched.

Added seeded grid baseline with full-turn-envelope occupancy and midpoint checks, reachable-goal BFS, collinear route compression and relative turn/drive skills. Runtime swept-envelope veto remains active. The baseline intentionally uses private simulator poses, so it must not be reported as visual agent performance. It currently assumes flat support ground and does not yet certify arbitrary multi-room terrain. Initial warehouse/Carter run grid-warehouse-001 launched on node43 GPU0, seed42. Realistic scene/asset diversity and support-surface checks remain required before batch deployment. New local unit suite: 12 passed. First rule-grid runtime validation is pending.

### Arena mainline and humanoid steering

User explicitly reaffirmed Arena as the task framework, then replaced Carter with G1 + SONIC motion tracking. No further legacy runner batches are authorized. Local Arena main was found newer than pinned remote 0.1.1; copied the pinned source for interface inspection. New adapters under prototypes/arena_navigation compose actual Arena Scene, EmbodimentBase and TaskBase via ArenaEnvBuilder; runtime verification is still pending.

Existing SONIC evidence establishes 300 Hz PhysX, 50 Hz encoder/decoder inference and 29 body joints with ThreeFinger hands. That test used a flat floor; warehouse was only a render backdrop. Therefore it does not establish warehouse obstacle navigation. The new G1 adapter declares physical joint-position targets and 300/50/30 Hz physics/control/render rates. Camera mounting, hands configuration, policy integration and in-scene stability remain to be verified. Grid paths require a motion-reference planning layer; the existing encoder/decoder alone cannot consume arbitrary XY waypoints. Keep high-speed acceptance based on measured trajectory and stability, not playback speed.

Arena G1 task probes 001/002 executed and exited, with reports retained in evidence. Probe001 failed because Arena's registry eagerly acquires two Lightwheel fixtures. A minimal patch defers only these assets' SDK imports and acquisition until their constructors; it is applied in a separate arena-0.1.1-mosaic copy, retaining the upstream source unchanged. Probe002 advanced to Isaac Lab's built-in pick/place imports, which require missing pin-pink. Preparing the declared pin-pink 3.1.0 dependency in the isolated overlay, with Python 3.11 wheels and numpy<2; runtime verification remains pending. Neither probe constructed a running Arena environment yet. Do not report task compatibility as passed.

Arena G1 probe004 completed 100 SONIC policy steps in the actual ArenaEnvBuilder-created Scene × Embodiment × Task environment, with 300 Hz physics, 50 Hz control and 29-dimensional joint position targets. Process exited normally. Across the two seconds, recorded root height was at least 0.71409 m; final XYZ was [-9.10534, 29.11511, 0.78317]. This verifies the control integration only: ego camera, full scene collision/visual fidelity, grid-reference planning and longer/faster locomotion remain unverified. Probe003 constructed the environment but failed reset due to a physics GPU mismatch; explicitly setting SimulationApp physics_gpu resolved it. Its shutdown remained live after the terminal failure report; sent SIGTERM only to the verified failed probe child.

IK overlay: all 16 wheel hashes verified; installed without bundled numpy/scipy replacement. pin-pink import passed; pin wheel distribution 2.7.0 reports native pinocchio version 2.6.21. Wheel manifest is committed for provenance. Isolated runtime is retained; this is not a change to the shared Isaac Sim installation.

Arena G1 ego probe007 completed 60 frames at 640×480 over two seconds. 150 Hz environment stepping schedules 50 Hz SONIC updates and 30 Hz records while physics stays 300 Hz. All 60 capture records have 43 joint positions/velocities and 29 control targets; timestamp spacing verified at 1/30 s. A downloaded middle frame visually confirms warehouse walls/floor/racking textures. Probes005/006 had empty image buffers because direct SimulationApp launch omitted /isaaclab/render/offscreen; setting the installed Isaac Lab flag resolved this. This is a short integration test, not yet grid navigation or high-speed stability acceptance. RouteReference adapter now encodes waypoint direction into the released SONIC planner interface but has not yet been runtime verified.

Arena grid/SONIC probe008 ran 12 seconds and recorded 360 ego frames / 1800 integration states. Grid route was (-9.10,29.05)→(-11.60,29.05)→(-11.60,31.05). Actual displacement was 0.92849 m, minimum root height 0.69336 m; it did not reach the first waypoint or trigger the conservative corridor/fall stop. Its old 'stepped' report field denotes runtime completion only, NOT navigation success. Updated route-mode report status to route_budget_exhausted. Probe009 is testing a 0.6 s planner execution window instead of 0.2 s, matching the earlier SONIC reference generator chunk duration; whether this improves motion remains unverified. Do not relax navigation/safety acceptance based on these probes.

SONIC upstream localmotion_kplanner.hpp (UpdatePlanning/UpdateContextFromMotion) shows continuous replanning takes four future samples from the previous reference, not four measured-history samples. Updated route wrapper to preserve this reference continuity while using measured XY for waypoint progress. Probes009/010 failed the explicit 51-frame tracker horizon check: variable planner output length makes a fixed 0.6 s execution window unsafe. Probe011 now requests a new reference early when the remaining horizon becomes insufficient, without padding/truncating to fake validity. It is running on GPU2. No navigation acceptance yet.

Probe011 completed 12 s without the reference-horizon exception. It advanced to waypoint2; final XY (-11.6053,30.2755), 0.7745 m from final goal; root height minimum 0.68230 m. Route acceptance remains false (budget exhausted). Added final-goal slowdown and a distinct 0.10 m final waypoint threshold instead of prematurely stopping at the intermediate 0.30 m radius. Next tests must also preserve terminal state across Arena automatic reset before claiming successful end-to-end recording. Future launchers snapshot prototype/scripts with SHA-256 manifest before starting.

Probe012 launches a 30 s route budget with end-goal slowdown, explicit source snapshots and single-episode Arena execution. SingleEpisodeEnv subclasses the actual Isaac Lab manager environment and suppresses only the automatic terminal reset during step; explicit reset remains available, and stepping after terminal is rejected. Goal termination requires <0.15 m distance and <0.03 m/s horizontal speed for 0.3 s. Runtime termination preservation must be verified from the resulting report before claiming acceptance. Partial/failure recordings are retained. Existing phase scope remains broader than this navigation integration diagnostic.
