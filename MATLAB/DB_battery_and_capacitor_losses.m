function [Pbatt_avg_tot_mtx,Pbatt_max_mtx,Pcap_avg_tot_mtx,Pcap_max_mtx,NcapI_mtx,Cap_Ipk_rating_fact,NcapP_mtx,Cap_Ppk_rating_fact,Pbatt_max_tot_mtx,Pcap_max_tot_mtx] = DB_battery_and_capacitor_losses(Params,Ibatt_avg_mtx,Ibatt_max_mtx,Icap_avg_mtx,Icap_max_mtx,Z_batt_mtx,Z_cap_mtx,NcapC_mtx,Cap_Ipk_mtx,NoofSM_total_mtx)
% Function to calculate the battery and capacitor losses
% [Pbatt_avg_tot_mtx,Pbatt_max_mtx,Pcap_avg_tot_mtx,Pcap_max_mtx,NcapI_mtx,Cap_Ipk_rating_fact,NcapP_mtx,Cap_Ppk_rating_fact,Pbatt_max_tot_mtx,Pcap_max_tot_mtx] = DB_battery_and_capacitor_losses(Params,Ibatt_avg_mtx,Ibatt_max_mtx,Icap_avg_mtx,Icap_max_mtx,Z_batt_mtx,Z_cap_mtx,NcapC_mtx,Cap_Ipk_mtx,NoofSM_total_mtx)
%

Z_cap_mtx(:,:,:,1) = 0; % Fore set capacitor impedance to 0 at DC (to avoid inf)
% this is not a problem becuase the cpacitor current at DC is 0
% (written in the previous section)

Pbatt_avg_mtx = squeeze(sum(Ibatt_avg_mtx.*conj(Ibatt_avg_mtx).*real(Z_batt_mtx),4)); % average battery losses
Pbatt_max_mtx = squeeze(sum(Ibatt_max_mtx.*conj(Ibatt_max_mtx).*real(Z_batt_mtx),4)); % maximum battery losses
Pcap_avg_mtx = squeeze(sum(Icap_avg_mtx.*conj(Icap_avg_mtx).*real(Z_cap_mtx),4)); % average capacitor losses
Pcap_max_mtx = squeeze(sum(Icap_max_mtx.*conj(Icap_max_mtx).*real(Z_cap_mtx),4)); % average capacitor losses

Icap_max_rms = sqrt(sum(abs(Icap_max_mtx).^2,4));

% NcapE_mtx = 0.5*Cap_C_mtx.*U_s_sw_mtx.^2./Ecap_pk;
% Acap_mtx  = NcapE_mtx*50e-6;

NcapI_mtx = Icap_max_rms./Cap_Ipk_mtx;
Cap_Ipk_rating_fact = NcapI_mtx./NcapC_mtx;
NcapP_mtx = Pcap_max_mtx./Params.P_cap_cell;
Cap_Ppk_rating_fact = NcapP_mtx./NcapC_mtx;

Pbatt_avg_tot_mtx = Pbatt_avg_mtx.*NoofSM_total_mtx; % total average battery losses
Pbatt_max_tot_mtx = Pbatt_max_mtx.*NoofSM_total_mtx; % total maximum battery losses
Pcap_avg_tot_mtx = Pcap_avg_mtx.*NoofSM_total_mtx; % total average capacitor losses
Pcap_max_tot_mtx = Pcap_max_mtx.*NoofSM_total_mtx; % total maximum capacitor losses
