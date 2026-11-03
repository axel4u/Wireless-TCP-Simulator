# Literature Review and References

## 1. Background

Transmission Control Protocol (TCP) provides reliable, ordered delivery and uses congestion-control mechanisms to regulate the amount of outstanding data. Traditional loss-based TCP mechanisms infer congestion from packet loss and respond by reducing the sending rate or congestion window. This approach is effective in many wired-network conditions, but wireless links can also lose packets because of channel errors, interference, and temporary connectivity disruptions. A sender that cannot distinguish these causes may apply congestion control even when the loss is not caused by a congested path.

The literature on wireless TCP has explored several ways to address this problem, including link-layer retransmission, local recovery, explicit loss notification, and end-to-end changes. The present project studies a small, sender-side, rule-based timeout-recovery policy in a discrete-event simulator. It uses simulated signal strength and queue delay as observable indicators, gives queue-delay congestion evidence priority, and falls back to standard timeout behaviour when the evidence is uncertain.

## 2. TCP congestion control and NewReno

Allman, Paxson, and Blanton describe the principal TCP congestion-control algorithms: slow start, congestion avoidance, fast retransmit, and fast recovery [1]. These mechanisms form the conceptual foundation for the baseline sender in this project. The implementation is intentionally simplified and should be described as a NewReno-style model, not as a complete standards-conformant TCP stack.

Henderson et al. specify the NewReno modification to fast recovery, including the sender's response to partial acknowledgements when multiple segments are lost within a window [2]. This is relevant to the project's baseline because its sender models duplicate-ACK recovery and partial/full acknowledgement behaviour. The project does not claim to implement every detail or every requirement of RFC 6582.

The retransmission timeout (RTO) is another important reliability mechanism. Paxson et al. specify how TCP senders compute and manage the retransmission timer [3]. The current simulator uses a fixed configurable RTO for experimental simplicity; it does not implement the full RTT estimation and timer computation procedure specified by the RFC. This difference should be stated explicitly in the methodology and limitations.

## 3. TCP performance over wireless links

Balakrishnan et al. explain that wireless and other lossy links can experience packet losses due to bit errors and handoffs, in addition to congestion losses. Their study compares end-to-end, link-layer, and split-connection approaches for improving TCP performance over wireless links [4]. The work provides the motivation for investigating whether a sender can avoid treating every loss as congestion.

Balakrishnan, Seshan, Amir, and Katz introduce the Snoop protocol, which performs local retransmissions at a base station while preserving end-to-end TCP semantics [5]. This is an important related approach, but it differs from the present project: the simulator does not implement a base-station cache or link-layer local retransmission protocol. Instead, it explores a simplified sender-side decision for timeout recovery using supplied link indicators.

These studies establish the broader research problem, but they do not validate the thresholds or performance of the policy implemented here. The project's thresholds are configurable experimental parameters and have not been calibrated against physical Wi-Fi measurements.

## 4. Burst-loss channel modelling

Gilbert introduced a two-state Markov model for burst-noise channels [6]. In this model, the channel alternates between states with different error characteristics. This is a foundation for representing temporally correlated errors rather than treating every transmission loss as an independent event.

Elliott further studied error-rate estimation for burst-noise channels and discussed the use of Gilbert's model [7]. These works motivate the project's use of a two-state GOOD/BAD Gilbert–Elliott channel abstraction. The simulator configures transition probabilities and state-dependent loss probabilities to generate bursts of packet loss.

The project's shared time-indexed burst trace is an experimental reproducibility mechanism layered on this statistical channel model. It aligns the channel state timeline by virtual simulation time for scenarios using the same seed. It is not a measured wireless trace, a physical RF model, or a guarantee that different algorithms transmit identical packets at identical times.

## 5. Research gap and project contribution

Prior work demonstrates that non-congestion-related losses can reduce TCP performance and that different protocol-layer mechanisms can mitigate the effect. This project narrows the investigation to a lightweight, rule-based sender-side timeout-recovery decision within a discrete-event simulator.

The implementation makes the following limited contributions:

1. It provides a simplified NewReno-style baseline for comparison.
2. It adds a rule-based adaptive timeout-recovery policy using simulated signal-strength and queue-delay inputs.
3. It explicitly prioritizes queue-delay congestion evidence over weak signal strength.
4. It uses an uncertain classification that preserves standard timeout recovery when evidence is insufficient.
5. It evaluates the policy using random and burst-loss channel abstractions, shared deterministic traces, multiple seeds, paired statistics, and a signal/queue-delay sensitivity sweep.

The contribution is an educational simulation study and prototype evaluation. It is not a new TCP standard, a production TCP implementation, or proof of real-world wireless performance. Validation using physical wireless telemetry or a more detailed network simulator remains future work.

## 6. References (IEEE style)

[1] M. Allman, V. Paxson, and E. Blanton, “TCP Congestion Control,” RFC 5681, Internet Engineering Task Force, Sep. 2009. doi: 10.17487/RFC5681. [Online]. Available: https://www.rfc-editor.org/rfc/rfc5681

[2] T. Henderson, S. Floyd, A. Gurtov, and Y. Nishida, “The NewReno Modification to TCP's Fast Recovery Algorithm,” RFC 6582, Internet Engineering Task Force, Apr. 2012. doi: 10.17487/RFC6582. [Online]. Available: https://www.rfc-editor.org/rfc/rfc6582

[3] V. Paxson, M. Allman, J. Chu, and M. Sargent, “Computing TCP's Retransmission Timer,” RFC 6298, Internet Engineering Task Force, Jun. 2011. doi: 10.17487/RFC6298. [Online]. Available: https://www.rfc-editor.org/rfc/rfc6298

[4] H. Balakrishnan, V. N. Padmanabhan, S. Seshan, and R. H. Katz, “A Comparison of Mechanisms for Improving TCP Performance over Wireless Links,” *IEEE/ACM Transactions on Networking*, vol. 5, no. 6, pp. 756–769, Dec. 1997, doi: 10.1109/90.650137.

[5] H. Balakrishnan, S. Seshan, E. Amir, and R. H. Katz, “Improving TCP/IP Performance over Wireless Networks,” in *Proc. 1st ACM International Conference on Mobile Computing and Networking (MobiCom)*, Berkeley, CA, USA, Nov. 1995, pp. 2–11, doi: 10.1145/215530.215544.

[6] E. N. Gilbert, “Capacity of a Burst-Noise Channel,” *Bell System Technical Journal*, vol. 39, no. 5, pp. 1253–1265, Sep. 1960, doi: 10.1002/j.1538-7305.1960.tb03959.x.

[7] E. O. Elliott, “Estimates of Error Rates for Codes on Burst-Noise Channels,” *Bell System Technical Journal*, vol. 42, no. 5, pp. 1977–1997, Sep. 1963, doi: 10.1002/j.1538-7305.1963.tb00955.x.

## 7. Notes for report integration

- Cite [1] and [2] in the TCP congestion-control and NewReno baseline sections.
- Cite [3] when discussing retransmission timeout concepts, then explain that this simulator uses a fixed RTO.
- Cite [4] and [5] in the problem statement and related-work section. Clearly distinguish the Snoop/link-layer approach from this project's sender-side simulation policy.
- Cite [6] and [7] in the wireless channel model section.
- Do not claim that the cited papers validate this project's exact policy thresholds or experimental outcomes.
- Use the same reference numbering consistently throughout the final report.
