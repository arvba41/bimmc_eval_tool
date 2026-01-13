function [Ploss_tot_avg_mtx,Ploss_tot_max_mtx,eff_tot_avg_mtx,eff_tot_max_mtx] = DB_totallosses_efficiency_calculation(Params,Pbatt_avg_tot_mtx,Pbatt_max_tot_mtx,Pcap_avg_tot_mtx,Pcap_max_tot_mtx,Psc_tot_avg_mtx,Psc_tot_max_mtx)
% Function to calculate the efficiencies and total losses
% 
% [Ploss_tot_avg_mtx,Ploss_tot_max_mtx,eff_tot_avg_mtx,eff_tot_max_mtx] = DB_totallosses_efficiency_calculation(Params,Pbatt_avg_tot_mtx,Pbatt_max_tot_mtx,Pcap_avg_tot_mtx,Pcap_max_tot_mtx,Psc_tot_avg_mtx,Psc_tot_max_mtx)

eff_battcap_avg_mtx = Params.Pout./(Params.Pout + Pbatt_avg_tot_mtx + Pcap_avg_tot_mtx); % Total semiconductor efficiency average
eff_sc_avg_mtx = Params.Pout./(Params.Pout + Psc_tot_avg_mtx); % Total semiconductor efficiency average
eff_tot_avg_mtx = Params.Pout./(Params.Pout + Psc_tot_avg_mtx + Pbatt_avg_tot_mtx + Pcap_avg_tot_mtx); % Total system efficiency average

eff_battcap_max_mtx = Params.Pout*Params.ocf./(Params.Pout*Params.ocf + Pbatt_max_tot_mtx + Pcap_max_tot_mtx); % Total semiconductor efficiency average
eff_sc_max_mtx = Params.Pout*Params.ocf./(Params.Pout*Params.ocf + Psc_tot_max_mtx); % Total semiconductor efficiency average
eff_tot_max_mtx = Params.Pout*Params.ocf./(Params.Pout*Params.ocf + Psc_tot_max_mtx + Pbatt_max_tot_mtx + Pcap_max_tot_mtx); % Total system efficiency average

Ploss_tot_avg_mtx = Psc_tot_avg_mtx + Pbatt_avg_tot_mtx + Pcap_avg_tot_mtx; % total losses as aveage power
Ploss_tot_max_mtx = Psc_tot_max_mtx + Pbatt_max_tot_mtx + Pcap_max_tot_mtx; % total losses as maximum power