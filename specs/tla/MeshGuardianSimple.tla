---------------------------- MODULE MeshGuardianSimple ----------------------------
(* Simplified model without restart limit *)

EXTENDS Integers, FiniteSets

CONSTANTS Nodes, MaxFailures

VARIABLES nodeState, failureCount

vars == <<nodeState, failureCount>>

TypeOK ==
    /\ nodeState \in [Nodes -> {"healthy", "unhealthy", "crashed", "restarting"}]
    /\ failureCount \in [Nodes -> 0..MaxFailures]

Init ==
    /\ nodeState = [n \in Nodes |-> "healthy"]
    /\ failureCount = [n \in Nodes |-> 0]

CrashedCount == Cardinality({n \in Nodes : nodeState[n] = "crashed"})

NodeFails(n) ==
    /\ nodeState[n] = "healthy"
    /\ nodeState' = [nodeState EXCEPT ![n] = "unhealthy"]
    /\ UNCHANGED failureCount

NodeCrashes(n) ==
    /\ nodeState[n] \in {"healthy", "unhealthy"}
    /\ CrashedCount < Cardinality(Nodes) - 1
    /\ nodeState' = [nodeState EXCEPT ![n] = "crashed"]
    /\ UNCHANGED failureCount

HealthCheck(n) ==
    /\ IF nodeState[n] = "healthy"
       THEN failureCount' = [failureCount EXCEPT ![n] = 0]
       ELSE /\ failureCount[n] < MaxFailures
            /\ failureCount' = [failureCount EXCEPT ![n] = failureCount[n] + 1]
    /\ UNCHANGED nodeState

GuardianRestart(n) ==
    /\ failureCount[n] >= MaxFailures
    /\ nodeState[n] \in {"unhealthy", "crashed"}
    /\ nodeState' = [nodeState EXCEPT ![n] = "restarting"]
    /\ failureCount' = [failureCount EXCEPT ![n] = 0]

RestartCompletes(n) ==
    /\ nodeState[n] = "restarting"
    /\ nodeState' = [nodeState EXCEPT ![n] = "healthy"]
    /\ UNCHANGED failureCount

NodeRecovers(n) ==
    /\ nodeState[n] = "unhealthy"
    /\ nodeState' = [nodeState EXCEPT ![n] = "healthy"]
    /\ failureCount' = [failureCount EXCEPT ![n] = 0]

Next == \E n \in Nodes :
    \/ NodeFails(n) \/ NodeCrashes(n) \/ HealthCheck(n)
    \/ GuardianRestart(n) \/ RestartCompletes(n) \/ NodeRecovers(n)

Fairness ==
    /\ \A n \in Nodes : WF_vars(HealthCheck(n))
    /\ \A n \in Nodes : WF_vars(GuardianRestart(n))
    /\ \A n \in Nodes : WF_vars(RestartCompletes(n))

Spec == Init /\ [][Next]_vars /\ Fairness

\* SAFETY
AtLeastOneAvailable ==
    \E n \in Nodes : nodeState[n] \in {"healthy", "unhealthy", "restarting"}

\* LIVENESS
EventualRecovery ==
    \A n \in Nodes : (nodeState[n] = "crashed") ~> (nodeState[n] = "healthy")

=============================================================================
