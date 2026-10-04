#pragma once
#include "../assets/fifa_player_assets.h"
#include <d3d11.h>
#include <memory>
namespace fifa_player {
/* Optional normalized inspection camera. No mesh/pose changes; default callers
 * retain their complete photographic framing. */
struct CameraFocus {float height_ratio=.72f,horizontal_ratio=0,span_ratio=.34f;};
struct StadiumCamera {Vec3 position={};float yaw=0,pitch=0;};
class Renderer {
    struct Mesh {
        ID3D11Buffer *vertices=nullptr,*indices=nullptr;UINT count=0;int texture=-1,hair_coeff_texture=-1;
        Vec3 color,tint,center={};bool blend=false,hair=false,actor=false;int surface=0;float alpha_scale=1;
        std::vector<uint32_t> strand_indices;
        std::vector<Vec3> strand_centers;
    };
    ID3D11Device *device_=nullptr;
    ID3D11DeviceContext *commands_=nullptr;
    ID3D11VertexShader *vs_=nullptr;
    ID3D11PixelShader *ps_=nullptr;
    ID3D11PixelShader *shadow_ps_=nullptr;
    ID3D11InputLayout *layout_=nullptr;
    ID3D11Buffer *constants_=nullptr;
    ID3D11SamplerState *sampler_=nullptr;
    ID3D11SamplerState *shadow_sampler_=nullptr;
    ID3D11RasterizerState *raster_=nullptr;
    ID3D11DepthStencilState *depth_state_=nullptr;
    ID3D11DepthStencilState *strand_depth_=nullptr;
    ID3D11BlendState *strand_blend_=nullptr;
    ID3D11ShaderResourceView *white_=nullptr,*image_=nullptr;
    ID3D11RenderTargetView *target_=nullptr;
    ID3D11DepthStencilView *depth_=nullptr;
    ID3D11DepthStencilView *shadow_depth_=nullptr;
    ID3D11ShaderResourceView *shadow_image_=nullptr;
    std::vector<Mesh> meshes_;
    std::vector<ID3D11ShaderResourceView *> textures_;
    std::shared_ptr<const Model> model_;
    UINT width_=0,height_=0;
    float low_=0,high_=180,extent_=180;
    float stadium_radius_=1;
    StadiumCamera stadium_camera_;bool free_stadium_=false;
    std::vector<Vec3> framing_points_;
    struct FramingPart {size_t first,count;float top;};
    std::vector<FramingPart> framing_parts_;
    UINT fitted_width_=0,fitted_height_=0;
    float fitted_yaw_=0,fitted_center_=0,fitted_distance_=0;
    bool fitted_portrait_=false,fitted_profile_=false;
    float fitted_crop_=-1;
    bool initialize();
    bool target(UINT width,UINT height);
    void release_model();
    void release_device();
public:
    ~Renderer(){release_device();}
    void device(ID3D11Device *);
    bool model(std::shared_ptr<const Model>);
    /* Profile is opt-in: transparent studio framing of one player only.
     * Team photos and all club rooms retain their existing scene/camera. */
    bool render(UINT width,UINT height,float yaw,float zoom,bool portrait=false,float pan_x=0,float pan_y=0,bool profile=false,float portrait_crop=.50f,const CameraFocus*focus=nullptr,bool transparent_background=false,float actor_x=0,float actor_y=0);
    StadiumCamera stadium_orbit_camera(UINT width,UINT height,float yaw,float zoom)const;
    bool render_stadium(UINT width,UINT height,float yaw,float zoom,const StadiumCamera*free_camera=nullptr);
    ID3D11ShaderResourceView *image() const{return image_;}
    void clear(){release_model();}
};
}
