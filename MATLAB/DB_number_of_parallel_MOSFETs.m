function [f_didt_calc,t_sw_max_mtx,dUds_mmc_percent_mtx,NoofParallel_mosfets_mtx,NoofParallel_actiVe_mosfets_mtx,Htfr_mtx,Rtheta_ca_mtx,return_var,Minimum_NoofParallel_mosfets_mtx] = DB_number_of_parallel_MOSFETs(Params,f,p_mtx,Cap_ESR_mtx,Cap_C_mtx,I_arm_max_mtx,I_sw_max_sw_mtx,I_sw_av_max_sw_mtx,RdsonMax_mtx,U_s_sw_mtx,Noofswitches_per_sm_mtx,check_mtx,Minimum_NoofParallel_mosfets_mtx)
% Function to calculate the number of parallel MOSFETs required 
%
% [f_didt_calc,t_sw_max_mtx,dUds_mmc_percent_mtx,NoofParallel_mosfets_mtx,NoofParallel_actiVe_mosfets_mtx,Htfr_mtx,Rtheta_ca_mtx,return_var] = DB_number_of_parallel_MOSFETs(Params,f,p_mtx,Cap_ESR_mtx,Cap_C_mtx,I_arm_max_mtx,I_sw_max_sw_mtx,I_sw_av_max_sw_mtx,RdsonMax_mtx,U_s_sw_mtx,Noofswitches_per_sm_mtx,check_sum)

global f_didt_min Rth_pad_mtx init_npmos_opti
%             dUds_mmc_mtx = Cap_ESR_mtx.*I_arm_max_mtx*sqrt(2) + Params.Lpcb.*Params.f_didt*1e6 + 1./Cap_C_mtx.*0.5.*I_arm_max_mtx*sqrt(2).*t_ri_max_mtx; % Delta Uds

% calculating didt

f_didt_calc = min(Params.f_didt,1./Params.Lpcb.*(Params.dUds*U_s_sw_mtx/100 - Cap_ESR_mtx.*I_arm_max_mtx*sqrt(2)));

%             dUds_mmc_percent_mtx_old = dUds_mmc_mtx./U_s_sw_mtx*100; % percentage overshoot
%             f_didt_calc(dUds_mmc_percent_mtx_old<=50) = Params.f_didt; % didt matrix

f_didt_calc(f_didt_calc<0) = Params.f_didt_min; % selecting minimum didt 

% recalculating the current fall times
% voltage and current switching transients
t_fv_max_mtx = U_s_sw_mtx./Params.f_dvdt; % voltage fall time
t_rv_max_mtx = U_s_sw_mtx./Params.r_dvdt; % voltage rise time
t_fi_max_mtx = I_sw_av_max_sw_mtx./f_didt_calc;
t_ri_max_mtx = I_sw_av_max_sw_mtx./f_didt_calc; % current rise time% recalculating the current fall times

% recalculating Delta uds
dUds_mmc_mtx_new = Cap_ESR_mtx.*I_arm_max_mtx*sqrt(2) + Params.Lpcb.*f_didt_calc + 1./Cap_C_mtx.*0.5.*I_arm_max_mtx*sqrt(2).*t_ri_max_mtx; % Delta Uds
dUds_mmc_percent_mtx = dUds_mmc_mtx_new./U_s_sw_mtx*100; % percentage overshoot

dTca = Params.Tc - Params.Ta; % case to ambient temperautre difference

t_sw_max_mtx = t_ri_max_mtx +t_fv_max_mtx + t_rv_max_mtx + t_fi_max_mtx; % switching transient maximum

%             NoofParallel_mosfets_mtx = 2*I_sw_max_sw_mtx.^2.*RdsonMax_mtx.*Params.Rca.*Noofswitches_per_sm_mtx./...
%                 (2*dTca - Noofswitches_per_sm_mtx.*Params.Rca.*U_s_sw_mtx.*I_sw_av_max_sw_mtx.*t_sw_max_mtx.*p_mtx*f); % number of parallel cells matrix

Htfr=Params.Rca; % Heat transfer coefficienct
%             Amos=4e-4;
% Rth_pad_mtx 

% k1=Noofswitches_per_sm_mtx/Htfr./(Params.Amos*Noofswitches_per_sm_mtx);
k2=I_sw_max_sw_mtx.^2.*RdsonMax_mtx;
k3=0.5*U_s_sw_mtx.*I_sw_av_max_sw_mtx.*t_sw_max_mtx.*p_mtx*f;
% dTca=k1/Np*(k2/Np+k3)=k1(k2/Np^2+k3/Np)
% x=1/Np: dTca=k1(k2*x^2+k3*x)=k1*k2*x^2+k1*k3*x
% x^2+k3/k2*x-dTca/(k1*k2)=0
% x=-k3./(2*k2)+sqrt(k3.^2./(2*k2).^2+dTca./(k1.*k2))
% NoofParallel_mosfets_mtx=1./x

x = -k3./(2*k2)+sqrt(k3.^2./(2*k2).^2 + dTca./(Rth_pad_mtx.*k2));
NoofParallel_mosfets_mtx=1./x;

%             A0_mtx=Noofswitches_per_sm_mtx*Params.Asw; % Heat transfer area 
% Included the capacitor area in the PCB area
A0_mtx=Noofswitches_per_sm_mtx*Params.Asw; % Heat transfer area 

% dTca=1/(Htfr*(A0+Amos*Np*Nsw))*(k2/Np+k3)*Nsw
% syms Nsw Htfr Amos A0 Np k2 k3 dTca
% solve(Nsw/(Htfr*(A0+Amos*Np*Nsw))*(k2/Np+k3)-dTca,Np)
%             NoofParallel_mosfets_mtx = ((A0^2*Htfr^2*dTca^2 - 2*A0*Htfr*Noofswitches_per_sm_mtx.*k3*dTca + 4*Htfr*Amos*k2.*Noofswitches_per_sm_mtx*dTca + Noofswitches_per_sm_mtx.^2.*k3.^2).^(1/2) + Noofswitches_per_sm_mtx.*k3 - A0*Htfr*dTca)/(2*Amos*Htfr*dTca);
% NoofParallel_mosfets_mtx = (Noofswitches_per_sm_mtx.*k3 + (A0_mtx.^2.*Htfr^2*dTca^2 - 2*Htfr*dTca*A0_mtx.*Noofswitches_per_sm_mtx.*k3 + 4*Params.Amos*Htfr*k2.*Noofswitches_per_sm_mtx.^2*dTca + Noofswitches_per_sm_mtx.^2.*k3.^2).^(1/2) - A0_mtx*Htfr*dTca)./(2*Params.Amos*Htfr*Noofswitches_per_sm_mtx*dTca);

% If the number of parallel MOSFETs is <0 or >NPmosmax, the maximum
% number of parlalel MOSFETs limit
% We recalculate the cae to ambient thermal resistance
%             Rtheta_ca_mtx = ones(size(NoofParallel_mosfets_mtx))*Params.Rca; % set-up matrix
NoofParallel_mosfets_mtx(NoofParallel_mosfets_mtx < 0 | NoofParallel_mosfets_mtx > Params.NPmosMax) = Params.NPmosMax; % check for maximum number of MOSFET limit

% solving for the negative constraint, when the number of
% mosfets yeild negative, we need to minitage this by
% calculating the Rthata_C using the following realtion

%             Rthata_ca_mtx_min = 2*dTca./(Noofswitches_per_sm_mtx.*U_s_mtx.*I_sw_av_max_sw_mtx.*t_sw_max_mtx.*Params.p*f);

%             Rtheta_ca_mtx(NoofParallel_mosfets_mtx < 0 | NoofParallel_mosfets_mtx > Params.NPmosMax) =  %
%             NoofParallel_mosfets_mtx_new = 2*I_sw_max_sw_mtx.^2.*RdsonMax_mtx.*Rtheta_ca_mtx.*Noofswitches_per_sm_mtx./...
%                 (2*dTca - Noofswitches_per_sm_mtx.*Rtheta_ca_mtx.*U_s_mtx.*I_sw_av_max_sw_mtx.*t_sw_max_mtx.*Params.p*f)

if init_npmos_opti == 1 
    Minimum_NoofParallel_mosfets_mtx = ones(size(NoofParallel_mosfets_mtx))*Params.NPmosMin; % Minimum numner of parallel MOSFETs vector
    init_npmos_opti = 0;
    return_var = 0;
    if length(check_mtx) == 1 
        return_var = 1;
    end
        
else
    % The following code is used for the optimization of minimum number of
    % parallel MOSFETs
    % if length(check_mtx) > 1
        check_sum = sum(check_mtx,'all');
    % else
        % do nothing 
    % end

    if ~check_sum
        return_var = 1;
        Minimum_NoofParallel_mosfets_mtx = Minimum_NoofParallel_mosfets_mtx - 1;
    else
        Minimum_NoofParallel_mosfets_mtx(check_mtx) = Minimum_NoofParallel_mosfets_mtx(check_mtx) + 1;
        return_var = 0;
    end
end



NoofParallel_actiVe_mosfets_mtx = max(NoofParallel_mosfets_mtx,Minimum_NoofParallel_mosfets_mtx); % Number of active parallel MOSFETS

% Rtheta_ca_mtx = 2*dTca*NoofParallel_actiVe_mosfets_mtx./(Noofswitches_per_sm_mtx.*(2.*I_sw_max_sw_mtx.^2.*RdsonMax_mtx + NoofParallel_actiVe_mosfets_mtx.*U_s_sw_mtx.*I_sw_av_max_sw_mtx.*t_sw_max_mtx.*p_mtx*f)); %
Apcb_mtx=Params.Amos*NoofParallel_actiVe_mosfets_mtx.*Noofswitches_per_sm_mtx;

Htfr_mtx = Htfr*ones(size(Apcb_mtx));
% Rtheta_ca_mtx=1./(Htfr_mtx.*Apcb_mtx);

Rtheta_ca_mtx = Rth_pad_mtx./(NoofParallel_actiVe_mosfets_mtx.*Noofswitches_per_sm_mtx);

% Accounting for negative values of f_didt_calc
f_didt_calc(f_didt_calc<f_didt_min) = inf;
t_sw_max_mtx(f_didt_calc<f_didt_min) = inf;
dUds_mmc_percent_mtx(f_didt_calc<f_didt_min) = inf;
NoofParallel_mosfets_mtx(f_didt_calc<f_didt_min) =inf;
NoofParallel_actiVe_mosfets_mtx(f_didt_calc<f_didt_min) = inf;
Htfr_mtx(f_didt_calc<f_didt_min) = inf;
Rtheta_ca_mtx(f_didt_calc<f_didt_min) = inf;
% Given the upper limit of the number of parallel MOSFETs, theNoofswitches_per_sm_mtx
% thermal resistance required to ensure that the