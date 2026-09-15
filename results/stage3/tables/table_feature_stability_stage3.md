**Stage 3 WP2. Development-only feature-stability diagnostic**

| source | action_id | AUROC_russellmitchell | AUROC_santos | AUROC_fox | AUROC_harrison | AUROC_wardbeck | direction_reverses | AUROC_r4.2 | AUROC_r5.2 |
|---|---|---|---|---|---|---|---|---|---|
| wp2_ait_AIT-EXFIL | ait_query_vpn | 0.539 | 0.427 | 0.479 | 0.457 | 0.501 | 0 | n/a | n/a |
| wp2_ait_AIT-EXFIL | ait_query_dns | 0.607 | 0.999 | 0.999 | 0.925 | 0.998 | 0 | n/a | n/a |
| wp2_ait_AIT-EXFIL | ait_query_web_access | 0.514 | 0.404 | 0.432 | 0.414 | 0.520 | 0 | n/a | n/a |
| wp2_ait_AIT-EXFIL | ait_query_web_error | 0.510 | 0.494 | 0.495 | 0.512 | 0.496 | 0 | n/a | n/a |
| wp2_ait_AIT-EXFIL | ait_query_auth | 0.503 | 0.491 | 0.523 | 0.500 | 0.503 | 0 | n/a | n/a |
| wp2_ait_AIT-EXFIL | ait_query_audit | 0.471 | 0.486 | 0.504 | 0.512 | 0.493 | 0 | n/a | n/a |
| wp2_ait_AIT-EXFIL | ait_query_ids | 0.478 | 0.977 | 0.484 | 0.981 | 0.523 | 0 | n/a | n/a |
| wp2_ait_AIT-EXFIL | ait_query_mail | 0.490 | 0.455 | 0.466 | 0.440 | 0.510 | 0 | n/a | n/a |
| wp2_ait_AIT-EXFIL | ait_query_syslog | 0.475 | 0.442 | 0.488 | 0.464 | 0.518 | 0 | n/a | n/a |
| wp2_ait_AIT-EXFIL | ait_query_monitoring | 0.539 | 0.496 | 0.346 | 0.616 | 0.498 | 1 | n/a | n/a |
| wp2_ait_AIT-INTRUSION | ait_query_vpn | 0.534 | 0.532 | 0.614 | 0.770 | 0.539 | 0 | n/a | n/a |
| wp2_ait_AIT-INTRUSION | ait_query_dns | 0.476 | 0.219 | 0.259 | 0.575 | 0.307 | 0 | n/a | n/a |
| wp2_ait_AIT-INTRUSION | ait_query_web_access | 0.265 | 0.716 | 0.786 | 0.887 | 0.713 | 1 | n/a | n/a |
| wp2_ait_AIT-INTRUSION | ait_query_web_error | 0.564 | 0.594 | 0.661 | 0.744 | 0.594 | 0 | n/a | n/a |
| wp2_ait_AIT-INTRUSION | ait_query_auth | 0.620 | 0.696 | 0.595 | 0.520 | 0.603 | 0 | n/a | n/a |
| wp2_ait_AIT-INTRUSION | ait_query_audit | 0.488 | 0.628 | 0.548 | 0.608 | 0.631 | 0 | n/a | n/a |
| wp2_ait_AIT-INTRUSION | ait_query_ids | 0.417 | 0.428 | 0.840 | 0.713 | 0.750 | 0 | n/a | n/a |
| wp2_ait_AIT-INTRUSION | ait_query_mail | 0.285 | 0.671 | 0.668 | 0.712 | 0.812 | 1 | n/a | n/a |
| wp2_ait_AIT-INTRUSION | ait_query_syslog | 0.476 | 0.762 | 0.653 | 0.768 | 0.745 | 0 | n/a | n/a |
| wp2_ait_AIT-INTRUSION | ait_query_monitoring | 0.910 | 0.883 | 0.923 | 0.736 | 0.986 | 0 | n/a | n/a |
| wp2_cert | cert_logon_afterhours | n/a | n/a | n/a | n/a | n/a | 0 | 0.545 | 0.528 |
| wp2_cert | cert_logon_pc_novelty | n/a | n/a | n/a | n/a | n/a | 0 | 0.499 | 0.710 |
| wp2_cert | cert_device_connects | n/a | n/a | n/a | n/a | n/a | 0 | 0.883 | 0.688 |
| wp2_cert | cert_file_copies | n/a | n/a | n/a | n/a | n/a | 0 | 0.826 | 0.651 |
| wp2_cert | cert_http_volume | n/a | n/a | n/a | n/a | n/a | 0 | 0.586 | 0.577 |
| wp2_cert | cert_http_domain_novelty | n/a | n/a | n/a | n/a | n/a | 0 | 0.558 | 0.539 |
| wp2_cert | cert_email_external | n/a | n/a | n/a | n/a | n/a | 0 | 0.508 | 0.544 |
| wp2_cert | cert_email_attachments | n/a | n/a | n/a | n/a | n/a | 0 | 0.484 | 0.563 |
| wp2_cert | cert_ldap_role_change | n/a | n/a | n/a | n/a | n/a | 0 | 0.399 | 0.454 |
| wp2_cert | cert_psychometric_neuroticism | n/a | n/a | n/a | n/a | n/a | 0 | 0.525 | 0.509 |
