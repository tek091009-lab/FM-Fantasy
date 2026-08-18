# V86 discipline current-state policy

Current suspension state must come from an explicit FM current-state decoder such as `discipline.dat/active-ban-v1`. Historical red/yellow-card rows remain factual event history and may be retained as diagnostic threshold candidates, but they are not sufficient to manufacture a live ban because competition thresholds, cut-offs, served fixtures, appeals and red-card lengths may vary.

The v86 pre/post guards preserve any explicit suspension evidence that exists before the v85 model finalizer, restore it after that finalizer, quarantine any `selected_competition_history_v85` derived ban as diagnostic-only evidence, and immediately re-run the direct availability truth sanitizer.
