# To learn more about how to use Nix to configure your environment
# see: https://developers.google.com/idx/guides/customize-idx-env
{ pkgs, ... }: {
  # Which nixpkgs channel to use.
  channel = "stable-23.11"; # or "unstable"
  # Use https://search.nixos.org/packages to find packages
  packages = [ 
    pkgs.python312 
    pkgs.gcc 
    pkgs.openssh
    pkgs.poetry
  ];
  idx = {
    # Search for the extensions you want on https://open-vsx.org/ and use "publisher.id"
    extensions = [ 
      "ms-python.python"
      # "ms-python.pylint"
      "ms-python.pylance"
      "humao.rest-client"
      "WakaTime.vscode-wakatime"
    ];
    workspace = {
      # Runs when a workspace is first created with this `dev.nix` file
      onCreate = {
        install-poetry-deps = "poetry install";
      };
      onStart = {
        poetry-update = "poetry update";
        run = "./start.sh";
      };
    };
  };
}
