---------------------------- MODULE MeshGuardian ----------------------------
(* AILinux Mesh Guardian - Formal Specification v1.1 *)
(* Bug found by TLC: MaxRestarts exhaustion = permanent death *)
(* Fix: Reset restartCount when node is stable *)

EXTENDS Integers, FiniteSets

CONSTANTS Nodes, MaxFailures, MaxRestarts

VARIABLES nodeState, failureCount, restartCount, guardianActive, lastHealthCheck

vars == <<nodeState, failureCount, restartCount, guardianActive, lastHealthCheck>>

TypeOK ==
    /\ nodeState \in [Nodes -> {"healthy", "unhealthy", "crashed", "restarting"}]
    /\ failureCount \in [Nodes -> 0..MaxFailures]
    /\ restartCount \in [Nodes -> 0..MaxRestarts]
    /\ guardianActive \in BOOLEAN
    /\ lastHealthCheck \in Nodes \cup {"-"}

Init ==
    /\ nodeState = [n \in Nodes |-> "healthy"]
    /\ failureCount = [n \in Nodes |-> 0]
    /\ restartCount = [n \in Nodes |-> 0]
    /\ guardianActive = TRUE
    /\ lastHealthCheck = "-"

CrashedCount == Cardinality({n \in Nodes : nodeState[n] = "crashed"})

NodeFails(n) ==
    /\ nodeState[n] = "healthy"
    /\ nodeState' = [nodeState EXCEPT ![n] = "unhealthy"]
    /\ UNCHANGED <<failureCount, restartCount, guardianActive, lastHealthCheck>>

NodeCrashes(n) ==
    /\ nodeState[n] \in {"healthy", "unhealthy"}
    /\ CrashedCount < Cardinality(Nodes) - 1
    /\ nodeState' = [nodeState EXCEPT ![n] = "crashed"]
    /\ UNCHANGED <<failureCount, restartCount, guardianActive, lastHealthCheck>>

HealthCheck(n) ==
    /\ guardianActive = TRUE
    /\ lastHealthCheck' = n
    /\ IF nodeState[n] = "healthy"
       THEN /\ failureCount' = [failureCount EXCEPT ![n] = 0]
            /\ UNCHANGED <<nodeState, restartCount, guardianActive>>
       ELSE /\ failureCount[n] < MaxFailures
            /\ failureCount' = [failureCount EXCEPT ![n] = failureCount[n] + 1]
            /\ UNCHANGED <<nodeState, restartCount, guardianActive>>

GuardianRestart(n) ==
    /\ guardianActive = TRUE
    /\ failureCount[n] >= MaxFailures
    /\ nodeState[n] \in {"unhealthy", "crashed"}
    /\ restartCount[n] < MaxRestarts
    /\ nodeState' = [nodeState EXCEPT ![n] = "restarting"]
    /\ restartCount' = [restartCount EXCEPT ![n] = restartCount[n] + 1]
    /\ failureCount' = [failureCount EXCEPT ![n] = 0]
    /\ UNCHANGED <<guardianActive, lastHealthCheck>>

RestartCompletes(n) ==
    /\ nodeState[n] = "restarting"
    /\ nodeState' = [nodeState EXCEPT ![n] = "healthy"]
    /\ UNCHANGED <<failureCount, restartCount, guardianActive, lastHealthCheck>>

NodeRecovers(n) ==
    /\ nodeState[n] = "unhealthy"
    /\ nodeState' = [nodeState EXCEPT ![n] = "healthy"]
    /\ failureCount' = [failureCount EXCEPT ![n] = 0]
    /\ UNCHANGED <<restartCount, guardianActive, lastHealthCheck>>

\* NEW: Reset restart counter when node is healthy and stable
\* This prevents permanent death after MaxRestarts
ResetRestartCount(n) ==
    /\ nodeState[n] = "healthy"
    /\ failureCount[n] = 0
    /\ restartCount[n] > 0
    /\ restartCount' = [restartCount EXCEPT ![n] = 0]
    /\ UNCHANGED <<nodeState, failureCount, guardianActive, lastHealthCheck>>

Next ==
    \E n \in Nodes :
        \/ NodeFails(n)
        \/ NodeCrashes(n)
        \/ HealthCheck(n)
        \/ GuardianRestart(n)
        \/ RestartCompletes(n)
        \/ NodeRecovers(n)
        \/ ResetRestartCount(n)

Fairness ==
    /\ \A n \in Nodes : WF_vars(HealthCheck(n))
    /\ \A n \in Nodes : WF_vars(GuardianRestart(n))
    /\ \A n \in Nodes : WF_vars(RestartCompletes(n))
    /\ \A n \in Nodes : WF_vars(ResetRestartCount(n))

Spec == Init /\ [][Next]_vars /\ Fairness

AtLeastOneAvailable ==
    \E n \in Nodes : nodeState[n] \in {"healthy", "unhealthy", "restarting"}

EventualRecovery ==
    \A n \in Nodes : (nodeState[n] = "crashed") ~> (nodeState[n] = "healthy")

EventualStability ==
    <>(\A n \in Nodes : nodeState[n] = "healthy")

=============================================================================
