function [NoofParallel_mosfets_mtx,NoofParallel_actiVe_mosfets_mtx,Rtheta_ca_mtx,Minimum_NoofParallel_mosfets_mtx] = DB_number_of_parallel_MOSFETs_discrete_DC_charging(Params,I_sw_max_sw_mtx,RdsonMax_mtx,Noofswitches_per_sm_mtx,Minimum_NoofParallel_mosfets_mtx,Rth_pad_mtx)
% Function to calculate the number of parallel MOSFETs required 
%
% [f_didt_calc,t_sw_max_mtx,dUds_mmc_percent_mtx,NoofParallel_mosfets_mtx,NoofParallel_actiVe_mosfets_mtx,Htfr_mtx,Rtheta_ca_mtx,return_var] = DB_number_of_parallel_MOSFETs(Params,f,p_mtx,Cap_ESR_mtx,Cap_C_mtx,I_arm_max_mtx,I_sw_max_sw_mtx,I_sw_av_max_sw_mtx,RdsonMax_mtx,U_s_sw_mtx,Noofswitches_per_sm_mtx,check_sum)

% global Rth_pad_mtx 

dTca = Params.Tc - Params.Ta; % case to ambient temperautre difference

NoofParallel_mosfets_mtx = I_sw_max_sw_mtx.*sqrt((Rth_pad_mtx.*RdsonMax_mtx)./dTca);

NoofParallel_mosfets_mtx(NoofParallel_mosfets_mtx < 0 | NoofParallel_mosfets_mtx > Params.NPmosMax) = Params.NPmosMax; % check for maximum number of MOSFET limit

% if init_npmos_opti == 1 
%     Minimum_NoofParallel_mosfets_mtx = ones(size(NoofParallel_mosfets_mtx))*Params.NPmosMin; % Minimum numner of parallel MOSFETs vector
%     init_npmos_opti = 0;
%     return_var = 0;
%     if length(check_mtx) == 1 
%         return_var = 1;
%     end
%         
% else
%     % The following code is used for the optimization of minimum number of
%     % parallel MOSFETs
%     % if length(check_mtx) > 1
%         check_sum = sum(check_mtx,'all');
%     % else
%         % do nothing 
%     % end
% 
%     if ~check_sum
%         return_var = 1;
%         Minimum_NoofParallel_mosfets_mtx = Minimum_NoofParallel_mosfets_mtx - 1;
%     else
%         Minimum_NoofParallel_mosfets_mtx(check_mtx) = Minimum_NoofParallel_mosfets_mtx(check_mtx) + 1;
%         return_var = 0;
%     end
% end



NoofParallel_actiVe_mosfets_mtx = max(NoofParallel_mosfets_mtx,Minimum_NoofParallel_mosfets_mtx); % Number of active parallel MOSFETS

% Rtheta_ca_mtx = 2*dTca*NoofParallel_actiVe_mosfets_mtx./(Noofswitches_per_sm_mtx.*(2.*I_sw_max_sw_mtx.^2.*RdsonMax_mtx + NoofParallel_actiVe_mosfets_mtx.*U_s_sw_mtx.*I_sw_av_max_sw_mtx.*t_sw_max_mtx.*p_mtx*f)); %
Apcb_mtx=Params.Amos*NoofParallel_actiVe_mosfets_mtx.*Noofswitches_per_sm_mtx;

% Htfr_mtx = Htfr*ones(size(Apcb_mtx));
% Rtheta_ca_mtx=1./(Htfr_mtx.*Apcb_mtx);

Rtheta_ca_mtx = Rth_pad_mtx./(NoofParallel_actiVe_mosfets_mtx.*Noofswitches_per_sm_mtx);

% Accounting for negative values of f_didt_calc
% f_didt_calc(f_didt_calc<f_didt_min) = inf;
% t_sw_max_mtx(f_didt_calc<f_didt_min) = inf;
% dUds_mmc_percent_mtx(f_didt_calc<f_didt_min) = inf;
% NoofParallel_mosfets_mtx(f_didt_calc<f_didt_min) =inf;
% NoofParallel_actiVe_mosfets_mtx(f_didt_calc<f_didt_min) = inf;
% Htfr_mtx(f_didt_calc<f_didt_min) = inf;
% Rtheta_ca_mtx(f_didt_calc<f_didt_min) = inf;
% Given the upper limit of the number of parallel MOSFETs, theNoofswitches_per_sm_mtx
% thermal resistance required to ensure that the